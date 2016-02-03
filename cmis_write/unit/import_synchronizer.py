# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 - Present Savoir-faire Linux
#    (<http://www.savoirfairelinux.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.connector.queue.job import job
import base64
import logging
_logger = logging.getLogger(__name__)


@job
def create_doc_in_edm(session, model_name, value, res,
                      dict_metadata, user_login, filters=None):
    """
    This method allows to create a doc from Odoo to DMS
    """
    cr = session.cr
    uid = session.uid
    context = session.context
    if context is None:
        context = {}
    ir_attach_obj = session.pool.get('ir.attachment')
    ir_attach_doc_backend_obj = session.pool.get('ir.attachment.doc.backend')
    cmis_backend_obj = session.pool.get('cmis.backend')

    # List of backend with storing_ok is True
    ids = cmis_backend_obj.search(
        cr, uid, [('storing_ok', '=', 'True')], context=context)

    for backend in session.browse('cmis.backend', ids):
        try:
            repo = cmis_backend_obj.check_auth(
                cr, uid, [backend.id], context=context)
            root = repo.rootFolder
            folder_path = backend.initial_directory_write
            # Document properties
            if value.get('name'):
                file_name = value.get('name')
            elif value.get('datas_fname'):
                file_name = value.get('datas_fname')
            else:
                file_name = value.get('datas_fname')
            props = {
                'cmis:name': file_name,
                'cmis:description': value.get('description'),
                'cmis:createdBy': user_login,
            }
            # Add list of metadata in props
            if len(dict_metadata):
                for k, v in dict_metadata.iteritems():
                    props[k] = v
            if folder_path:
                sub1 = repo.getObjectByPath(folder_path)
            else:
                sub1 = root
            someDoc = sub1.createDocumentFromString(
                file_name,
                contentString=base64.b64decode(
                    value.get('datas')), contentType=value.get('file_type')
            )
            # TODO: create custom properties on a document (Alfresco)
            # someDoc.getProperties().update(props)
            # Updating ir.attachment object with the new id
            # of document generated by DMS
            ir_attach_obj.write(cr, uid, res, {
                'id_dms': someDoc.getObjectId()}, context=context)
            ir_attach_doc_backend_obj.create(
                cr, uid, {
                    'attachment_id': res,
                    'backend_id': backend.id,
                    'object_doc_id': someDoc.getObjectId(),
                }, context=context)
            _logger.warn('Attachment saved in DMS %s', backend.name)
        except:
            _logger.warn('Cannot save the attachment in DMS %s', backend.name)
            continue
    return True