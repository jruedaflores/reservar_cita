# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

from ..utils.expression import UNLINK_USER_ERROR_MSG


class RcParamsConfig(models.Model):
    _name = 'rc.params.config'
    _inherit = ['mail.thread']
    _description = "Representa parámetros del sistema asociados a las configuraciones generales."

    name = fields.Char('Nombre', copy=False,  required=True, readonly=1)
    key = fields.Char('Código interno', copy=False,  required=True)
    value = fields.Char('Valor', copy=False,  required=True, tracking=True)

    _sql_constraints = [
        ('name_uniq', 'unique (key)', """¡El valor ya existe!"""),
    ]

    def unlink(self):
        raise UserError(UNLINK_USER_ERROR_MSG)
