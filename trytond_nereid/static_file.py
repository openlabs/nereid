# -*- coding: UTF-8 -*-
'''
    nereid.static_file

    Static file

    :copyright: (c) 2011-2012 Openlabs Technologies & Consulting (P) Limited
    :copyright: (c) 2010 by Sharoon Thomas.
    :license: GPLv3, see LICENSE for more details
'''
import os
import urllib

from nereid.helpers import slugify, send_file, url_for
from nereid.globals import _request_ctx_stack
from werkzeug import abort

from trytond.model import ModelSQL, ModelView, fields
from trytond.config import CONFIG
from trytond.transaction import Transaction
from trytond.pyson import Eval, Not, Equal


# pylint: disable-msg=E1101

class NereidStaticFolder(ModelSQL, ModelView):
    "Static folder for Nereid"
    _name = "nereid.static.folder"
    _description = __doc__
    _rec_name = 'folder_name'

    folder_name = fields.Char(
        'Folder Name', required=True, select=1,
        on_change_with=['name', 'folder_name']
    )
    description = fields.Char('Description', select=1)
    files = fields.One2Many('nereid.static.file', 'folder', 'Files')

    def __init__(self):
        super(NereidStaticFolder, self).__init__()
        self._constraints += [
            ('check_folder_name', 'invalid_folder_name'),
        ]
        self._sql_constraints += [
            ('unique_folder', 'UNIQUE(folder_name)',
             'Folder name needs to be unique')
        ]
        self._error_messages.update({
            'invalid_folder_name': """Invalid folder name:
                (1) '.' in folder name (OR)
                (2) folder name begins with '/'""",
            'folder_cannot_change': "Folder name cannot be changed"
        })

    def on_change_with_folder_name(self, vals):
        """
        Fills the name field with a slugified name
        """
        if vals.get('name'):
            if not vals.get('folder_name'):
                vals['folder_name'] = slugify(vals['name'])
            return vals['folder_name']

    def check_folder_name(self, ids):
        '''
        Check the validity of folder name
        Allowing the use of / or . will be risky as that could
        eventually lead to previlege escalation

        :param ids: ID of current record.
        '''
        folder = self.browse(ids[0])
        if ('.' in folder.folder_name) or (folder.folder_name.startswith('/')):
            return False
        return True

    def write(self, ids, vals):
        """
        Check if the folder_name has been modified.
        If yes, raise an error.

        :param vals: values of the current record
        """
        if vals.get('folder_name'):
            # TODO: Support this feature in future versions
            self.raise_user_error('folder_cannot_change')
        return super(NereidStaticFolder, self).write(ids, vals)


NereidStaticFolder()


class NereidStaticFile(ModelSQL, ModelView):
    "Static files for Nereid"
    _name = "nereid.static.file"
    _description = __doc__

    name = fields.Char('File Name', select=True, required=True)
    folder = fields.Many2One(
        'nereid.static.folder', 'Folder', select=True, required=True
    )
    type = fields.Selection([
        ('local', 'Local File'),
        ('remote', 'Remote File'),
    ], 'File Type')

    #: URL of the remote file if the :attr:`type` is remote
    remote_path = fields.Char('Remote File', select=True, translate=True,
        states = {
            'required': Equal(Eval('type'), 'remote'),
            'invisible': Not(Equal(Eval('type'), 'remote'))
        }
    )

    #: This function field returns the field contents. This is useful if the
    #: field is going to be displayed on the clients.
    file_binary = fields.Function(
        fields.Binary('File'), 'get_file_binary', 'set_file_binary',
    )

    #: Full path to the file in the filesystem
    file_path = fields.Function(fields.Char('File Path'), 'get_file_path')

    #: URL that can be used to idenfity the resource. Note that the value
    #: of this field is available only when called within a request context.
    #: In other words the URL is valid only when called in a nereid request. 
    url = fields.Function(fields.Char('URL'), 'get_url')

    def __init__(self):
        super(NereidStaticFile, self).__init__()
        self._constraints += [
            ('check_file_name', 'invalid_file_name'),
        ]
        self._sql_constraints += [
            ('name_folder_uniq', 'UNIQUE(name, folder)',
                'The Name of the Static File must be unique in a folder.!'),
        ]
        self._error_messages.update({
            'invalid_file_name': """Invalid file name:
                (1) '..' in file name (OR)
                (2) file name contains '/'""",
        })

    def default_type(self):
        return 'local'

    def get_url(self, ids, name):
        """Return the url if within an active request context or return
        False values
        """
        res = {}.fromkeys(ids, False)
        if _request_ctx_stack.top is None:
            return res

        for f in self.browse(ids):
            if f.type == 'local':
                res[f.id] = url_for(
                    'nereid.static.file.send_static_file',
                    folder=f.folder.folder_name, name=f.name
                )
            elif f.type == 'remote':
                res[f.id] = f.remote_path
        return res

    def get_nereid_base_path(self):
        """
        Returns base path for nereid, where all the static files would be
        stored.

        By Default it is:

        <Tryton Data Path>/<Database Name>/nereid
        """
        cursor = Transaction().cursor
        return os.path.join(
            CONFIG['data_path'], cursor.database_name, "nereid"
        )

    def set_file_binary(self, ids, name, value):
        """
        Setter for the functional binary field.

        :param ids: List of ids. But usually has just one
        :param name: Ignored
        :param value: The file buffer
        """
        for f in self.browse(ids):
            if f.type == 'local':
                file_binary = buffer(value)
                # If the folder does not exist, create it recursively
                directory = os.path.dirname(f.file_path)
                if not os.path.isdir(directory):
                    os.makedirs(directory)
                with open(f.file_path, 'wb') as file_writer:
                    file_writer.write(file_binary)

    def get_file_binary(self, ids, name):
        '''
        Getter for the binary_file field. This fetches the file from the
        file system, coverts it to buffer and returns it.

        :param ids: the ids of the sales
        :return: Dictionary with ID as key and file buffer as value
        '''
        res = {}
        for f in self.browse(ids):
            location = f.file_path if f.type == 'local' \
                else urllib.urlretrieve(f.remote_path)[0]
            with open(location, 'rb') as file_reader:
                res[f.id] = buffer(file_reader.read())
        return res

    def get_file_path(self, ids, name):
        """
        Returns the full path to the file in the file system

        :param ids: the ids of the sales
        :return: Dictionary with ID as key and binary
        """
        res = {}
        for f in self.browse(ids):

            res[f.id] = os.path.abspath(
                os.path.join(
                    self.get_nereid_base_path(), f.folder.folder_name, f.name
                )) \
            if f.type == 'local' else f.remote_path
        return res

    def check_file_name(self, ids):
        '''
        Check the validity of folder name
        Allowing the use of / or . will be risky as that could
        eventually lead to previlege escalation

        :param ids: ID of current record.
        '''
        file_ = self.browse(ids[0])
        if ('..' in file_.name) or ('/' in file_.name):
            return False
        return True

    def send_static_file(self, folder, name):
        """
        Invokes the send_file method in nereid.helpers to send a file as the
        response to the reuqest. The file is sent in a way which is as 
        efficient as possible. For example nereid will use the X-Send_file
        header to make nginx send the file if possible.

        :param folder: folder_name of the folder
        :param name: name of the file
        """
        #TODO: Separate this search and find into separate cached method

        ids = self.search([
            ('folder.folder_name', '=', folder),
            ('name', '=', name)
            ])
        if not ids:
            abort(404)
        file_ = self.browse(ids[0])
        return send_file(file_.file_path)

NereidStaticFile()
