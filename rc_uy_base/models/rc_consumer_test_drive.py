import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..utils.expression import UNLINK_USER_ERROR_MSG
from ..utils.common import get_schedule_created, can_create_schedule


class RcConsumerTestDrive(models.Model):
    _name = 'rc.consumer.test.drive'
    _inherit = ['mail.thread']
    _description = "Representa los Exámenes (teórica o práctica) asociados a la persona."
    _rec_name = 'consumer_id'
    _order = 'date_start desc'

    consumer_id = fields.Many2one('rc.consumer', 'Consumidor', domain="[('state','=','active')]", required=True)
    date_start = fields.Datetime(string='Horario Comienzo', required=True)
    date_stop = fields.Datetime(string='Horario Terminación', required=True)
    state = fields.Selection([('draft', 'Borrador'), ('planned', 'Planificada'), ('scheduled', 'Agendada'),
                              ('approved', 'Aprobada'), ('suspended', 'Suspendida'), ('canceled', 'Cancelada')],
                             string='Estado', default="draft",
                             readonly=True, tracking=True)
    type = fields.Selection([('theoric', 'Teórico'), ('practical', 'Práctico')], string='Tipo', required=True)
    note = fields.Text('Nota', tracking=True)
    resource_id = fields.Many2one('rc.resource', 'Recurso', related='consumer_id.resource_id')
    booking_id = fields.Many2one('rc.booking', 'Reserva', readonly=True)

    # _sql_constraints = [
    #     ('name_uniq', 'unique (consumer_id,date)', """¡El valor ya existe!"""),
    # ]

    def action_planned(self):
        self.state = 'planned'

    def action_automatic_scheduled(self):
        self.state = 'scheduled'

    def action_scheduled(self):
        if self.consumer_id.resource_id:
            schedule_ids = get_schedule_created(self, self.date_start.date())
            schedule_values = {
                'date_start': self.date_start,
                'date_stop': self.date_stop,
                'resource_id': self.consumer_id.resource_id.id,
            }
            if can_create_schedule(schedule_ids, schedule_values):
                schedule_values_id = self.env['rc.schedule'].create(schedule_values)
            else:
                schedule_search = [('date_start', '=', self.date_start), ('date_stop', '=', self.date_stop),
                                   ('resource_id', '=', self.consumer_id.resource_id.id), ('state', '!=', 'booked')]
                schedule_values_id = self.env['rc.schedule'].search(schedule_search, limit=1)

            if schedule_values_id:
                if schedule_values_id.state in ('draft', 'locked'):
                    schedule_values_id.action_available()

                booking_values = {
                    'schedule_id': schedule_values_id.id,
                    'consumer_id': self.consumer_id.id,
                    'resource_id': schedule_values.get('resource_id'),
                }
                booking_id = self.env['rc.booking'].create(booking_values)
                booking_id.action_automatic_confirmed()
                self.booking_id = booking_id.id
                self.state = 'scheduled'
            else:
                raise UserError(_("No es posible realizar la operación. Fecha no disponible."))
        else:
            raise UserError(_("No es posible realizar la operación. Datos incompletos."))

    def action_approved(self):
        if self.booking_id.state == 'confirmed':
            self.booking_id.action_done()
        self.state = 'approved'

    def action_suspended(self):
        if self.booking_id.state == 'confirmed':
            self.booking_id.action_done()
        self.state = 'suspended'

    def action_automatic_canceled(self):
        self.state = 'canceled'

    def action_canceled(self):
        if self.booking_id.state == 'confirmed':
            self.booking_id.action_canceled_admin()
        self.state = 'canceled'

    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise UserError(UNLINK_USER_ERROR_MSG)
        return super(RcConsumerTestDrive, self).unlink()

    @api.onchange('date_start')
    def onchange_date_start(self):
        if self.date_start:
            booking_time_id = self.env['rc.params.config'].search([('key', '=', 'booking_time')])
            booking_time = int(booking_time_id.value) or 0
            self.date_stop = self.date_start + datetime.timedelta(hours=booking_time)
