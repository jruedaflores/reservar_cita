import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression

from ..utils.expression import UNLINK_USER_ERROR_MSG, WRITE_USER_ERROR_MSG, WEEKDAYS, HOURS_TIMEZONE_BASE
from ..utils.common import convert_utc_to_local

STATE_LIST = [('draft', 'Borrador'), ('available', 'Disponible'), ('booked', 'Reservado'), ('locked', 'Bloqueado')]

STATE_JSON = {
    STATE_LIST[0][0]: STATE_LIST[0][1],
    STATE_LIST[1][0]: STATE_LIST[1][1],
    STATE_LIST[2][0]: STATE_LIST[2][1],
    STATE_LIST[3][0]: STATE_LIST[3][1]
}


def _common_name_get(date_start, date_stop):
    weekday = WEEKDAYS[date_start.weekday()][1]
    date_start_utc = convert_utc_to_local(date_start)
    date_start_utc = date_start_utc.strftime("%d-%m-%Y %H:%M")
    date_stop_utc = convert_utc_to_local(date_stop)
    date_stop_utc = date_stop_utc.strftime("%H:%M")
    name = '{} {} - {}'.format(weekday, date_start_utc, date_stop_utc)
    return name


class RcSchedule(models.Model):
    _name = 'rc.schedule'
    _inherit = ['mail.thread']
    _description = "Repesenta la Agenda (calendario) de cada recurso."
    _order = 'date_start desc'

    # todo: validar que en el alta/modif. no se solapen lasa agendas. ver metodo de generar agenda automatica
    @api.model
    def _get_default_calendar_view(self):
        rec_name = super(RcSchedule, self)._get_default_calendar_view()
        return STATE_JSON.get(rec_name, False) or rec_name

    date_start = fields.Datetime(string='Horario Comienzo', required=True, states={'booked': [('readonly', True)]})
    date_stop = fields.Datetime(string='Horario Terminación', required=True, states={'booked': [('readonly', True)]})
    state = fields.Selection(STATE_LIST, string='Estado', default="draft", readonly=True, tracking=True, required=True)
    resource_id = fields.Many2one('rc.resource', 'Recurso', required=True, states={'booked': [('readonly', True)]})
    booking_ids = fields.One2many('rc.booking', 'schedule_id', string='Reserva', readonly=True)
    booking_name = fields.Char('Reservado por', compute='_compute_booking_name')
    is_booked = fields.Boolean('Reservado', compute='_compute_booking_name')

    _sql_constraints = [
        ('name_uniq', 'unique (date_start, resource_id)', """¡El valor ya existe!"""),
    ]

    def write(self, values):
        if self.state == 'draft' or (values.get('state') and len(values) == 1):
            res = super(RcSchedule, self).write(values)
        else:
            raise UserError(WRITE_USER_ERROR_MSG)
        return res

    def name_get(self):
        result = []
        if self._context.get('calendar_views'):
            for schedule in self:
                if len(self.ids) == 1:
                    name = _common_name_get(schedule.date_start, schedule.date_stop)
                elif schedule.is_booked:
                    name = schedule.booking_name
                else:
                    name = STATE_JSON.get(schedule.state, False)
                result.append((schedule.id, name))
        else:
            for schedule in self:
                name = _common_name_get(schedule.date_start, schedule.date_stop)
                result.append((schedule.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            if name.isnumeric() and len(name) <= 2:
                days = name
                hours = str(int(name) + HOURS_TIMEZONE_BASE)
                domain = ['|', ('date_start', '=ilike', '%' + days + ' %'),
                          ('date_start', '=ilike', '% ' + hours + '%')]

            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        schedule_ids = self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(schedule_ids).with_user(name_get_uid))

    def unlink(self):
        for item in self:
            if item.state == 'booked':
                raise UserError(UNLINK_USER_ERROR_MSG)
        return super(RcSchedule, self).unlink()

    def action_available(self):
        for rec in self:
            if rec.state not in ('draft', 'locked'):
                raise UserError(_("Para realizar dicha operación las Agenda deben estar en estado Borrador o Bloqueado."))
            rec.state = 'available'

    def action_locked(self):
        for rec in self:
            if rec.state not in ('draft', 'available'):
                raise UserError(_("Para realizar dicha operación las Agenda deben estar en estado Borrador o Disponible."))
            rec.state = 'locked'

    @api.onchange('date_start')
    def onchange_date_start(self):
        if self.date_start:
            booking_time_id = self.env['rc.params.config'].search([('key', '=', 'booking_time')])
            booking_time = int(booking_time_id.value) or 0
            self.date_stop = self.date_start + datetime.timedelta(hours=booking_time)

    @api.depends('booking_ids', 'booking_ids.state')
    def _compute_booking_name(self):
        for schedule in self:
            booking_ok = False
            booking_name = _("No reservado")
            if schedule.state == 'booked':
                for booking_id in schedule.booking_ids:
                    if booking_id.state in ('confirmed', 'absent', 'done'):
                        if not booking_ok:
                            booking_ok = True
                            booking_name = booking_id.consumer_id.name
                        else:
                            booking_ok = False
                            booking_name = _("Error: Al menos 2 reservas coinciden.")

            schedule.booking_name = booking_name
            schedule.is_booked = booking_ok
