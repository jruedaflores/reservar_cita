import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..utils.expression import UNLINK_USER_ERROR_MSG
from ..utils.common import convert_hour_to_minute, calculate_time_in_minutes


class RcBooking(models.Model):
    _name = 'rc.booking'
    _inherit = ['mail.thread']
    _description = "Representa la Reserva realizada de un recurso."
    _order = 'schedule_id desc'
    _rec_name = 'consumer_id'

    def _is_admin_user_group(self):
        return True if self.env.user.has_group('rc_uy_base.rc_admin_user_group') else False

    def _default_consumer_id(self):
        if self._is_admin_user_group():
            return False

        consumer_id = self.env['rc.consumer'].search([('users_id', '=', self.env.uid)], limit=1)
        return consumer_id.id or False

    def _default_admin_user(self):
        return True if self._is_admin_user_group() else False

    state = fields.Selection(
        [('draft', 'Borrador'), ('confirmed', 'Confirmada'), ('absent', 'Ausentado'), ('done', 'Realizada'),
         ('canceled', 'Cancelada')], string='Estado', default="draft", readonly=True, tracking=True)
    consumer_id = fields.Many2one('rc.consumer', 'Consumidor', domain="[('state','=','active')]", required=True,
                                  default=_default_consumer_id)
    resource_id = fields.Many2one('rc.resource', 'Recurso', domain="[('state','=', 'active')]", required=True)
    schedule_id = fields.Many2one('rc.schedule', 'Agenda', required=True,
                                  domain="[('state','=', 'available'), ('resource_id','=', resource_id)]")
    date_start = fields.Datetime(related='schedule_id.date_start', store=False)
    date_stop = fields.Datetime(related='schedule_id.date_stop', store=False)
    is_cancellable = fields.Boolean('Es cancelable', compute='_compute_boolean_fields')
    is_admin_user = fields.Boolean('Es usuario admin', compute='_compute_boolean_fields', default=_default_admin_user)
    has_test_drive = fields.Boolean('Tiene exámenes activos?', default=False)

    # _sql_constraints = [
    #     ('name_uniq', 'unique (consumer_id,schedule_id,state)', """¡El valor ya existe!"""),
    # ]

    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise UserError(UNLINK_USER_ERROR_MSG)
        return super(RcBooking, self).unlink()

    def action_automatic_confirmed(self):
        self.action_confirmed()
        self.has_test_drive = True

    def action_confirmed(self):
        if self.state != 'draft':
            raise UserError(_("Para realizar dicha operación las Reservas deben estar en estado Borrador."))

        if not self._context.get('active_model', False) and self.schedule_id.state != 'available':
            raise UserError(_("La fecha seleccionada no está disponible en estos momentos."))

        if not self._is_admin_user_group():
            now = datetime.datetime.utcnow()
            if now >= self.date_start:
                raise UserError(_("La fecha seleccionada no está disponible. Debe seleccionar un turno posterior a la "
                                  "fecha – hora actual."))

            week = self.date_start.isocalendar()[1]
            weekly_booking_ids = self.consumer_id.booking_ids.filtered(
                lambda reg: reg.state in ('confirmed', 'absent', 'done') and reg.date_start.isocalendar()[1] == week)

            weekly_booking_total = calculate_time_in_minutes(self.date_stop, self.date_start)
            for booking_id in weekly_booking_ids:
                weekly_booking_total += calculate_time_in_minutes(booking_id.date_stop, booking_id.date_start)

            if weekly_booking_total > convert_hour_to_minute(self.consumer_id.weekly_booking_qty):
                raise UserError(_("Con la reserva, se supera el máximo de horas de reservaciones semanales."))

        self.sudo().schedule_id.state = 'booked'
        self.state = 'confirmed'

    def action_done(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Para realizar dicha operación las Reservas deben estar en estado Confirmada."))
            rec.state = 'done'

    def action_absent(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Para realizar dicha operación las Reservas deben estar en estado Confirmada."))
            rec.state = 'absent'

    def _common_action_canceled(self):
        self.sudo().schedule_id.state = 'available'
        self.state = 'canceled'
        if self.has_test_drive:
            test_drive_ids = self.env['rc.consumer.test.drive'].search([('booking_id', '=', self.id)])
            for test_id in test_drive_ids:
                test_id.action_automatic_canceled()

    def _common_compute_is_cancellable(self):
        is_cancellable = False
        if self.date_start:
            time_config_id = self.env['rc.params.config'].search([('key', '=', 'time_before_action_canceled')])
            time_before_action_cancel = int(time_config_id.value) or 0
            now = datetime.datetime.utcnow()
            if (now + datetime.timedelta(hours=int(time_before_action_cancel))) <= self.date_start:
                is_cancellable = True
        return is_cancellable

    def action_canceled(self):
        if not self._common_compute_is_cancellable():
            raise UserError(_("Venció el plazo de cancelación de la booking. Contacte con personal de administración."))
        self._common_action_canceled()

    def action_canceled_admin(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Para realizar dicha operación las Reservas deben estar en estado Confirmada."))
            rec._common_action_canceled()

    def action_create_test_drive(self):
        for rec in self:
            if rec.state == 'confirmed':
                test_values = {
                    'consumer_id': self.consumer_id.id,
                    'type': 'practical',
                    'resource_id': self.resource_id.id,
                    'booking_id': self.id,
                    'date_start': self.date_start,
                    'date_stop': self.date_stop,
                }
                test_drive_id = self.env['rc.consumer.test.drive'].create(test_values)
                test_drive_id.action_automatic_scheduled()
                self.has_test_drive = True

    @api.onchange('consumer_id')
    def onchange_consumer_id(self):
        if not self._context.get('active_model', False) and self.consumer_id:
            self.resource_id = self.consumer_id.resource_id or False

    def _compute_boolean_fields(self):
        for booking in self:
            booking.is_cancellable = booking._common_compute_is_cancellable()
            booking.is_admin_user = True if booking._is_admin_user_group() else False
