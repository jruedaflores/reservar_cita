from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..utils.expression import ACTIVE_USER_ERROR_MSG, UNLINK_USER_ERROR_MSG
from ..utils.common import convert_hour_to_minute, calculate_time_in_minutes


class RcConsumer(models.Model):
    _name = 'rc.consumer'
    _inherit = ['mail.thread']
    _description = "Representa la Persona que consume la reserva."
    _order = 'name'

    name = fields.Char('Nombre', copy=False, required=True)
    ci = fields.Char('Cédula de Identidad', copy=False, required=True)
    email = fields.Char('Email', required=True, help=_("Email (usuario) de conexión al sistema."))
    phone = fields.Char('Teléfono')
    mobile = fields.Char('Móvil')
    mobile_emergency = fields.Char('Emergencia Móvil')
    street = fields.Char('Dirección')
    city = fields.Char('Localidad')
    society = fields.Char('Sociedad')
    state = fields.Selection([('draft', 'Borrador'), ('inactive', 'Inactivo'), ('active', 'Activo')],
                             string='Estado', default="draft", readonly=True, tracking=True)
    resource_id = fields.Many2one('rc.resource', 'Recurso', domain="[('state','=', 'active')]", tracking=True)
    users_id = fields.Many2one('res.users', 'Usuario', readonly=1)
    booking_ids = fields.One2many('rc.booking', 'consumer_id', string=' Reservas')
    booking_qty = fields.Integer(string='Totales contratadas', help="Cantidad total de reservas.", tracking=True)
    booked_qty = fields.Float(string='Confirmadas', compute='_compute_booking_qty',
                              help="Cantidad de reservas confirmadas.")
    available_booked_qty = fields.Float(string='Disponibles', compute='_compute_booking_qty',
                                        help="Cantidad de reservas disponibles.")
    weekly_booking_qty = fields.Integer(string='Reservas semanales (Hrs)', tracking=True
                                        , help="Cantidad máxima de reservas semanales permitidas.")
    test_drive_ids = fields.One2many('rc.consumer.test.drive', 'consumer_id', string=' Exámenes')
    active = fields.Boolean('Activo', help=ACTIVE_USER_ERROR_MSG, default=True, tracking=True)

    _sql_constraints = [
        ('name_uniq', 'unique (ci)', """¡El valor ya existe!"""),
    ]

    def _create_user(self):
        user_values = {
            "name": self.name,
            "login": self.email,
            "password": self.email.split("@")[0],
            "action_id": self.env.ref('rc_uy_base.action_rc_reserva').id
        }
        return self.env["res.users"].create(user_values)

    def action_active(self):
        self.state = 'active'
        if not self.users_id:
            users_id = self._create_user()
            users_id.groups_id += self.env.ref('rc_uy_base.rc_consumer_user_group')
            self.users_id = users_id
        else:
            self.users_id.active = True
        return True

    def action_inactive(self):
        self.state = 'inactive'
        self.resource_id = False
        if self.users_id:
            self.users_id.active = False
        return True

    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise UserError(UNLINK_USER_ERROR_MSG)
            if self.users_id:
                self.users_id.active = False
        return super(RcConsumer, self).unlink()

    @api.depends('booking_ids')
    def _compute_booking_qty(self):
        config_booking_time_id = self.env['rc.params.config'].search([('key', '=', 'booking_time')])
        config_booking_time_minutes = convert_hour_to_minute(config_booking_time_id.value)
        for consumer in self:
            qty = 0
            for booking_id in self.booking_ids:
                if booking_id.state in ('done', 'absent'):
                    booking_time_minutes = calculate_time_in_minutes(booking_id.date_stop, booking_id.date_start)
                    qty += (booking_time_minutes / config_booking_time_minutes)
            consumer.booked_qty = qty
            consumer.available_booked_qty = consumer.booking_qty - qty
