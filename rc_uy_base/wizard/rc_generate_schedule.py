# -*- coding: utf-8 -*-
import datetime

from odoo import fields, models, _
from ..utils.common import convert_local_date_to_utc, get_schedule_created, can_create_schedule


class RcGenerateScheduleDay(models.TransientModel):
    _name = 'rc.generate.schedule.day'
    _rec_name = 'day'

    day = fields.Date('Día', required=True)
    rc_generate_schedule_id = fields.Many2one('rc.generate.schedule', string='Generar Agenda')


class RcGenerateScheduleHour(models.TransientModel):
    _name = 'rc.generate.schedule.hour'

    def _default_hour_start(self):
        booking_time_id = self.env['rc.params.config'].search([('key', '=', 'booking_hour_start')])
        return int(booking_time_id.value) or 0

    def _default_reserve_time(self):
        booking_time_id = self.env['rc.params.config'].search([('key', '=', 'booking_time')])
        return int(booking_time_id.value) or 0

    def _default_hour_end(self):
        booking_time_id = self.env['rc.params.config'].search([('key', '=', 'booking_hour_end')])
        return int(booking_time_id.value) or 0

    hour_start = fields.Float('Hora Inicio', default=_default_hour_start)
    reserve_time = fields.Float('Duración', default=_default_reserve_time)
    hour_end = fields.Float('Hora Fin', default=_default_hour_end)
    rc_generate_schedule_id = fields.Many2one('rc.generate.schedule', string='Generar Agenda')


class RcGenerateSchedule(models.TransientModel):
    _name = 'rc.generate.schedule'
    _description = 'Generar agendas'

    rc_generate_schedule_day_ids = fields.One2many('rc.generate.schedule.day', 'rc_generate_schedule_id',
                                                   string=' Días', required=True)
    rc_generate_schedule_hour_ids = fields.One2many('rc.generate.schedule.hour', 'rc_generate_schedule_id',
                                                   string=' Horarios', required=True)
    resource_ids = fields.Many2many(string="Recursos", comodel_name='rc.resource',
                                    help=_("Representa los Recursos a tener en cuenta para la generación de la agenda. "
                                           "Si no se selecciona ninguno, se tendrán en cuenta todos los Recursos "
                                           "activos."))

    def action_generate_schedule(self):
        resource_ids = self.resource_ids or False
        if not resource_ids:
            resource_ids = self.env['rc.resource'].search([('state', '=', 'active'), ('active', '=', True)])

        schedule_vals_list = []
        for day_id in self.rc_generate_schedule_day_ids:
            schedule_ids = get_schedule_created(self, day_id.day)
            for hour_id in self.rc_generate_schedule_hour_ids:
                reserve_time = hour_id.hour_start
                while reserve_time < hour_id.hour_end:
                    date_start = datetime.datetime(day_id.day.year, day_id.day.month, day_id.day.day) \
                                 + datetime.timedelta(hours=reserve_time)
                    date_start_utc = convert_local_date_to_utc(date_start)
                    date_stop_utc = date_start_utc + datetime.timedelta(hours=hour_id.reserve_time)
                    for resource_id in resource_ids:
                        schedule_vals = {
                            'date_start': date_start_utc,
                            'date_stop': date_stop_utc,
                            'resource_id': resource_id.id
                        }
                        if can_create_schedule(schedule_ids, schedule_vals):
                            schedule_vals_list.append(schedule_vals)

                    reserve_time += hour_id.reserve_time

        if schedule_vals_list:
            self.env['rc.schedule'].create(schedule_vals_list)
        return True
