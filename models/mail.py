# -*- coding: utf-8 -*-

from openerp import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)

class ProcessMails(models.Model):
    _inherit = "mail.message"

    @api.model
    def create(self, vals):
        mail = super(ProcessMails, self).create(vals)
        if mail.message_type in ['email'] and mail.attachment_ids:
            dte = False
            for att in mail.attachment_ids:
                if not att.name:
                    continue
                name = att.name.upper()
                if att.mimetype in ['text/plain'] and name.find('.XML') > -1:
                    if not self.env['mail.message.dte'].search([('name', '=', name)]):
                        dte = {
                            'mail_id': mail.id,
                            'name': name,
                        }
            if dte:
                val = self.env['mail.message.dte'].create(dte)
                val.pre_process()
                val.mail_id = mail
        return mail

class ProccessMail(models.Model):
    _name = 'mail.message.dte'
    _inherit = ['mail.thread']

    name = fields.Char(
        string="Nombre Envío",
        readonly=True,
    )
    mail_id = fields.Many2one(
        'mail.message',
        string="Email",
        readonly=True,
        ondelete='cascade',
    )
    document_ids = fields.One2many(
        'mail.message.dte.document',
        'dte_id',
        string="Documents",
        readonly=True,
    )

    def pre_process(self):
        self.process_message(pre=True)

    @api.multi
    def process_message(self, pre=False):
        for r in self:
            for att in r.mail_id.attachment_ids:
                if not att.name:
                    continue
                name = att.name.upper()
                if att.mimetype in ['text/plain'] and name.find('.XML') > -1:
                    vals={
                        'xml_file': att.datas,
                        'filename': att.name,
                        'pre_process': pre,
                        'dte_id': r.id,
                    }
                    val = self.env['sii.dte.upload_xml.wizard'].create(vals)
                    created = val.confirm()

class ProcessMailsDocument(models.Model):
    _name = 'mail.message.dte.document'
    _inherit = ['mail.thread']

    dte_id = fields.Many2one(
        'mail.message.dte',
        string="DTE",
        readonly=True,
        ondelete='cascade',
    )
    new_partner = fields.Char(
        string="Proveedor Nuevo",
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        domain=[('supplier', '=', True)],
    )
    date = fields.Date(
        string="Fecha Emsisión",
        readonly=True,
    )
    number = fields.Char(
        string='Folio',
        readonly=True,
    )
    sii_document_class_id = fields.Many2one(
        'sii.document_class',
        string="Tipo de Documento",
        readonly=True,
    )
    amount = fields.Monetary(
        string="Monto",
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id,
    )
    invoice_line_ids = fields.One2many(
        'mail.message.dte.document.line',
        'document_id',
        string="Líneas del Documento",
    )
    company_id = fields.Many2one(
        'res.company',
        string="Compañía",
        readonly=True,
    )
    state= fields.Selection(
        [
            ('draft','Recibido'),
            ('acepted', 'Aceptado'),
            ('rejected', 'Rechazado'),
        ],
        default='draft',
    )
    invoice_id = fields.Many2one(
        'account.invoice',
        string="Factura",
        readonly=True,
    )

    @api.multi
    def acept_document(self):
        created = []
        for r in self:
            for att in r.dte_id.sudo().mail_id.attachment_ids:
                if not att.name:
                    continue
                name = att.name.upper()
                if att.mimetype in ['text/plain'] and name.find('.XML') > -1:
                    vals={
                        'xml_file': att.datas,
                        'filename': att.name,
                        'pre_process': False,
                        'document_id': r.id,
                    }
                    val = self.env['sii.dte.upload_xml.wizard'].create(vals)
                    created = val.confirm()
            r.state = 'acepted'
        xml_id = 'account.action_invoice_tree2'
        result = self.env.ref('%s' % (xml_id)).read()[0]
        invoice_domain = eval(result['domain'])
        invoice_domain.append(('id', 'in', created))
        result['domain'] = invoice_domain
        return result

    @api.multi
    def reject_document(self):
        for r in self:
            for att in r.dte_id.sudo().mail_id.attachment_ids:
                if not att.name:
                    continue
                name = att.name.upper()
                if att.mimetype in ['text/plain'] and name.find('.XML') > -1:
                    vals={
                        'xml_file': att.datas,
                        'filename': att.name,
                        'pre_process': False,
                        'document_id': r.id,
                        'option': 'reject',
                    }
                    val = self.env['sii.dte.upload_xml.wizard'].create(vals)
                    created = val.confirm()
            r.state = 'rejected'


class ProcessMailsDocumentLines(models.Model):
    _name = 'mail.message.dte.document.line'

    document_id = fields.Many2one(
        'mail.message.dte.document',
        string="Documento",
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        string="Producto",
    )
    new_product = fields.Char(
        string='Nuevo Producto',
        readonly=True,
    )
    description = fields.Char(
        string='Descripción',
        readonly=True,
    )
    product_description = fields.Char(
        string='Descripción Producto',
        readonly=True,
    )
    quantity = fields.Float(
        string="Cantidad",
        readonly=True,
    )
    price_unit = fields.Monetary(
        string="Precio Unitario",
        readonly=True,
    )
    price_subtotal = fields.Monetary(
        string="Total",
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id,
    )
