from odoo import models, fields, api, _

TIMEZONE_BASE = 'America/Montevideo'
HOURS_TIMEZONE_BASE = 3
ACTIVE_USER_ERROR_MSG = _("Si el campo Activo se establece en Falso, le permitirá ocultar registro sin eliminarlo.")
UNLINK_USER_ERROR_MSG = _("No puede eliminar registros en estados válidos. Deberías archivarlos.")
WRITE_USER_ERROR_MSG = _("No puede modificar registros en estados válidos.")

WEEKDAYS = [('0', 'Lunes'), ('1', 'Martes'), ('2', u'Miércoles'), ('3', 'Jueves'), ('4', 'Viernes'), ('5', u'Sábado'),
            ('6', 'Domingo')]

MONTHS = [('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'), ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
          ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'), ('10', 'Octubre'), ('11', 'Noviembre'),
          ('12', 'Diciembre')]