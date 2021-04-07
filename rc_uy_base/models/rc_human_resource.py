from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..utils.expression import ACTIVE_USER_ERROR_MSG, UNLINK_USER_ERROR_MSG


class RcHumanResource(models.Model):
    _name = 'rc.human.resource'
    _inherit = ['mail.thread']
    _description = "Repesenta el Recurso Humano que es reservado por la persona."
    _order = 'name'

    name = fields.Char('Nombre', copy=False,  required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Borrador'), ('inactive', 'Inactivo'), ('active', 'Activo')],
                             string='Estado', default="draft", readonly=True, tracking=True)
    email = fields.Char('Email', required=True, help=_("Email utilizado para el usuario conectarse al sistema."))
    users_id = fields.Many2one('res.users', 'Usuario', readonly=1)
    resource_id = fields.Many2one('rc.resource', 'Recurso')
    # resource_ids = fields.Many2many('rc.resource', 'rc_human_resource_resource_rel', 'human_id', 'resource_id',
    #                                 string='Recursos')
    active = fields.Boolean('Activo', help=ACTIVE_USER_ERROR_MSG, default=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', """¡El valor ya existe!"""),
    ]

    def _create_user(self):
        user_values = {
            "name": self.name,
            "login": self.email,
            "password": self.email.split("@")[0],
            "rc_human_resource_id": self.id
        }
        return self.env["res.users"].create(user_values)

    def action_active(self):
        self.state = 'active'
        if not self.users_id:
            users_id = self._create_user()
            users_id.groups_id += self.env.ref('rc_uy_base.rc_resource_user_group')
            self.users_id = users_id
        else:
            self.users_id.active = True
        return True

    def action_inactive(self):
        self.state = 'inactive'
        if self.users_id:
            self.users_id.active = False
        return True

    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise UserError(UNLINK_USER_ERROR_MSG)
            if self.users_id:
                self.users_id.active = False
        return super(RcHumanResource, self).unlink()


class ResUsers(models.Model):
    _inherit = 'res.users'

    rc_human_resource_id = fields.Many2one('rc.human.resource', 'Recurso persona', readonly=1)
