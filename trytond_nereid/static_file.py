#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
    nereid.static_file

    Static file

    :copyright: (c) 2010 by Sharoon Thomas.
    :license: BSD, see LICENSE for more details
'''
import os
import base64
from collections import defaultdict

from nereid.helpers import slugify, send_file
from werkzeug import abort

from trytond.model import ModelSQL, ModelView, fields
from trytond.config import CONFIG
from trytond.transaction import Transaction


def get_nereid_path():
    "Returns base path for nereid"
    cursor = Transaction().cursor
    return os.path.join(CONFIG['data_path'], cursor.database_name)


def make_folder_path(folder_name):
    "Returns the folder path for given folder"
    return os.path.join(get_nereid_path(), folder_name)


def make_file_path(folder_name, file_name):
    "Returns the file path for the given folder, file"
    return os.path.join(make_folder_path(folder_name), file_name)


def make_file(file_name, file_binary, folder):
    """
    Writes file to the FS

    :param file_name: Name of the file
    :param file_binary: Binary content to save (Base64 encoded)
    :param folder: folder name
    """
    file_binary = base64.decodestring(file_binary)
    file_path = make_file_path(folder, file_name)
    with open(file_path, 'wb') as file_writer:
        file_writer.write(file_binary)
    return file_path


# pylint: disable-msg=E1101

class NereidStaticFolder(ModelSQL, ModelView):
    "Static folder for Nereid"
    _name = "nereid.static.folder"
    _description = __doc__

    name = fields.Char('Description', required=True, select=1)
    folder_name = fields.Char('Folder Name', required=True, select=1,
        on_change_with=['name', 'folder_name'])
    comments = fields.Text('Comments')
    files = fields.One2Many('nereid.static.file', 'folder', 'Files')
    folder_path = fields.Function(fields.Char('Folder Path'), 'get_path')
    
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


    def get_path(self, ids, name):
        """Return the path of the folder
        """
        result = { }
        for folder in self.browse(ids):
            result[folder.id] = make_folder_path(folder.folder_name)
        return result

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

    def create(self, vals):
        """
        Check if the folder exists.
        If not, create a new one in data path of tryton.

        :param vals: values of the current record
        """
        folder_path = make_folder_path(vals.get('folder_name'))

        # Create the nereid folder if it doesnt exist
        if not os.path.isdir(get_nereid_path()):
            os.mkdir(get_nereid_path())

        # Create the folder if it doesnt exist
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)

        return super(NereidStaticFolder, self).create(vals)

    def write(self, ids, vals):
        """
        Check if the folder_name has been modified. 
        If yes, raise an error.

        :param vals: values of the current record
        """
        if vals.get('folder_name'):
            self.raise_user_error('folder_cannot_change')
        return super(NereidStaticFolder, self).write(ids, vals)

    def scan_files_from_fs(self, folder_ids):
        """
        Scans File system for images and syncs them

        :param folder_ids: ID of the System Folder 
        """
        file_object = self.pool.get('nereid.static.file')

        for folder in self.browse(folder_ids):
            existing_filenames = [f.name for f in folder.files]

            folder_path = make_folder_path(folder.folder_name)
            for content in os.listdir(folder_path):
                full_path = os.path.join(folder_path, content)

                if (os.path.isfile(full_path)) and \
                            (content not in existing_filenames):
                    file_object.create({'name': content, 'folder': folder.id})
        return True

NereidStaticFolder()


class NereidStaticFile(ModelSQL, ModelView):
    "Static files for Nereid"
    _name = "nereid.static.file"
    _description = __doc__

    name = fields.Char('File Name', select=True, required=True)
    file_ = fields.Function(fields.Binary('File'), 
        'get_field_binary', 'set_content')
    folder = fields.Many2One('nereid.static.folder', 'Folder', required=True)
    file_path = fields.Function(fields.Char('File Path'), 'get_fields',)
    relative_path = fields.Function(fields.Char('Relative Path'), 'get_fields')

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

    def set_content(self, ids, name, value):
        """
        Creates the file for the function field
        """
        for file_ in self.browse(ids):
            make_file(file_.name, value, file_.folder.folder_name)

    def get_fields(self, ids, names):
        '''
        Function to compute function fields for sale ids

        :param ids: the ids of the sales
        :param names: the list of field name to compute
        :return: a dictionary with all field names as key and
            a dictionary as value with id as key
        '''
        res = defaultdict(dict)
        for name in names:
            res[name] = { }

        for file_ in self.browse(ids):
            file_path = os.path.join(
                make_file_path(file_.folder.folder_name, file_.name))

            if 'file_path' in names:
                res['file_path'][file_.id] = file_path


            if 'relative_path' in names:
                res['relative_path'][file_.id] = '/'.join([
                    file_.folder.folder_name, 
                    file_.name])

        return res

    def get_field_binary(self, ids, name):
        """
        This could be part of the above function, but this is an 
        expensive process which must not affect the rest of the processes
        """
        result = {}
        for file_ in self.browse(ids):
            file_path = os.path.join(
                make_file_path(file_.folder.folder_name, file_.name))
            with open(file_path, 'rb') as file_handler:
                result[file_.id] = base64.encodestring(
                        file_handler.read()
                    )
        return result

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
        '''
        Send the static file
        '''
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
