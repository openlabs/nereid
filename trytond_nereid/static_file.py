# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import os
import mimetypes

from nereid import route
from nereid.helpers import send_file, url_for
from nereid.globals import _request_ctx_stack
from werkzeug import abort

from trytond.model import ModelSQL, ModelView, fields
from trytond.config import config
from trytond.transaction import Transaction
from trytond.pyson import Eval, Bool
from trytond import backend

__all__ = ['NereidStaticFolder', 'NereidStaticFile']

READONLY_IF_FILES = {
    'readonly': Bool(Eval('files'))
}


class NereidStaticFolder(ModelSQL, ModelView):
    "Static folder for Nereid"
    __name__ = "nereid.static.folder"

    name = fields.Char(
        'Name', required=True, select=True, states=READONLY_IF_FILES,
        depends=['files']
    )
    description = fields.Char(
        'Description', select=True, states=READONLY_IF_FILES,
        depends=['files']
    )
    files = fields.One2Many('nereid.static.file', 'folder', 'Files')
    type = fields.Selection([
        ('local', 'Local File'),
    ], 'File Type', states=READONLY_IF_FILES, depends=['files'])

    @classmethod
    def __setup__(cls):
        super(NereidStaticFolder, cls).__setup__()
        cls._sql_constraints += [
            ('unique_folder', 'UNIQUE(name)',
             'Folder name needs to be unique')
        ]
        cls._error_messages.update({
            'invalid_name': """Invalid folder name:
                (1) '.' in folder name (OR)
                (2) folder name begins with '/'""",
        })

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        cursor = Transaction().cursor
        table = TableHandler(cursor, cls, module_name)

        table.column_rename('folder_name', 'name')

        super(NereidStaticFolder, cls).__register__(module_name)

    @classmethod
    def validate(cls, folders):
        """
        Validates the records.

        :param folders: active record list of folders
        """
        super(NereidStaticFolder, cls).validate(folders)
        for folder in folders:
            folder.check_name()

    @staticmethod
    def default_type():
        return 'local'

    def check_name(self):
        '''
        Check the validity of folder name
        Allowing the use of / or . will be risky as that could
        eventually lead to previlege escalation
        '''
        if ('.' in self.name) or (self.name.startswith('/')):
            self.raise_user_error('invalid_name')


class NereidStaticFile(ModelSQL, ModelView):
    "Static files for Nereid"
    __name__ = "nereid.static.file"

    name = fields.Char('File Name', select=True, required=True)
    folder = fields.Many2One(
        'nereid.static.folder', 'Folder', select=True, required=True
    )

    #: This function field returns the field contents. This is useful if the
    #: field is going to be displayed on the clients.
    file_binary = fields.Function(
        fields.Binary('File', filename='name'),
        'get_file_binary', 'set_file_binary',
    )

    #: Full path to the file in the filesystem
    file_path = fields.Function(fields.Char('File Path'), 'get_file_path')

    #: URL that can be used to idenfity the resource. Note that the value
    #: of this field is available only when called within a request context.
    #: In other words the URL is valid only when called in a nereid request.
    url = fields.Function(fields.Char('URL'), 'get_url')

    # Sequence
    sequence = fields.Integer('Sequence', select=True)

    # File mimetype
    mimetype = fields.Function(fields.Char('Mimetype'), getter='get_mimetype')

    @classmethod
    def __setup__(cls):
        super(NereidStaticFile, cls).__setup__()
        cls._sql_constraints += [
            ('name_folder_uniq', 'UNIQUE(name, folder)',
                'The Name of the Static File must be unique in a folder.!'),
        ]
        cls._error_messages.update({
            'invalid_file_name': """Invalid file name:
                (1) '..' in file name (OR)
                (2) file name contains '/'""",
        })

    @staticmethod
    def default_sequence():
        return 10

    def get_mimetype(self, name):
        """
        This method detects and returns the mimetype for the static file.

        The python mimetypes module returns a tuple of the form -:

        >>> mimetypes.guess_type(file_name)
        (file_mimetype, encoding)

        which can then be used to fill the `mimetype` field. Some example types
        are -:
            * image/png
            * application/pdf
        etc.
        """
        return mimetypes.guess_type(self.name)[0]

    def get_url(self, name):
        """Return the url if within an active request context or return
        False values
        """
        if _request_ctx_stack.top is None:
            return None

        return url_for(
            'nereid.static.file.send_static_file',
            folder=self.folder.name, name=self.name
        )

    @staticmethod
    def get_nereid_base_path():
        """
        Returns base path for nereid, where all the static files would be
        stored.

        By Default it is:

        <Tryton Data Path>/<Database Name>/nereid
        """
        cursor = Transaction().cursor
        return os.path.join(
            config.get('database', 'path'), cursor.database_name, "nereid"
        )

    def _set_file_binary(self, value):
        """
        Setter for static file that stores file in file system

        :param value: The value to set
        """
        file_binary = buffer(value)
        # If the folder does not exist, create it recursively
        directory = os.path.dirname(self.file_path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with open(self.file_path, 'wb') as file_writer:
            file_writer.write(file_binary)

    @classmethod
    def set_file_binary(cls, files, name, value):
        """
        Setter for the functional binary field.

        :param files: Records
        :param name: Ignored
        :param value: The file buffer
        """
        for static_file in files:
            static_file._set_file_binary(value)

    def get_file_binary(self, name):
        '''
        Getter for the binary_file field. This fetches the file from the
        file system, coverts it to buffer and returns it.

        :param name: Field name
        :return: File buffer
        '''
        location = self.file_path
        with open(location, 'rb') as file_reader:
            return buffer(file_reader.read())

    def get_file_path(self, name):
        """
        Returns the full path to the file in the file system

        :param name: Field name
        :return: File path
        """
        return os.path.abspath(
            os.path.join(
                self.get_nereid_base_path(),
                self.folder.name, self.name
            ))

    @classmethod
    def validate(cls, files):
        """
        Validates the records.

        :param files: active record list of static files
        """
        super(NereidStaticFile, cls).validate(files)
        for file in files:
            file.check_file_name()

    def check_file_name(self):
        '''
        Check the validity of folder name
        Allowing the use of / or . will be risky as that could
        eventually lead to previlege escalation
        '''
        if ('..' in self.name) or ('/' in self.name):
            self.raise_user_error("invalid_file_name")

    @classmethod
    @route("/static-file/<folder>/<name>", methods=["GET"])
    def send_static_file(cls, folder, name):
        """
        Invokes the send_file method in nereid.helpers to send a file as the
        response to the request. The file is sent in a way which is as
        efficient as possible. For example nereid will use the X-Send_file
        header to make nginx send the file if possible.

        :param folder: name of the folder
        :param name: name of the file
        """
        # TODO: Separate this search and find into separate cached method

        files = cls.search([
            ('folder.name', '=', folder),
            ('name', '=', name)
        ])
        if not files:
            abort(404)
        return send_file(files[0].file_path)
