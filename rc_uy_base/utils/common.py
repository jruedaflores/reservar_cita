from datetime import datetime, time
import pytz

from .expression import TIMEZONE_BASE


def convert_local_date_str_to_utc(date_str):
    date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    date_obj_utc = convert_local_date_to_utc(date_obj)
    date_str_utc = date_obj_utc.strftime('%Y-%m-%d %H:%M:%S')
    return date_str_utc


def convert_local_date_to_utc(date_obj):
    date_obj_utc = False
    if date_obj:
        zk_timezone = pytz.timezone(TIMEZONE_BASE)
        date_obj = zk_timezone.localize(date_obj, is_dst=None)
        date_obj = date_obj.astimezone(pytz.utc)
        date_obj_utc = date_obj.replace(tzinfo=None)
    return date_obj_utc


def convert_utc_to_local(date_obj):
    date_obj_local = False
    if date_obj:
        zk_timezone = pytz.timezone(TIMEZONE_BASE)
        date_obj_dt = date_obj.replace(tzinfo=pytz.utc)
        date_obj_local = date_obj_dt.astimezone(zk_timezone)
        date_obj_local = date_obj_local.replace(tzinfo=None)
    return date_obj_local


def get_schedule_created(self, day):
    date_start = datetime.combine(day, time.min)
    date_stop = datetime.combine(day, time.max)
    schedule_ids = self.env['rc.schedule'].search_read([('date_start', '>=', date_start),
                                                        ('date_start', '<=', date_stop)],
                                                       ['date_start', 'date_stop', 'resource_id'])
    return schedule_ids


def can_create_schedule(schedule_ids, schedule_vals):
    for schedule_id in schedule_ids:
        condition_resource = schedule_vals.get('resource_id') == schedule_id.get('resource_id')[0]
        condition_date_start = schedule_id.get('date_start') <= schedule_vals.get('date_start') < schedule_id.get('date_stop')
        condition_date_stop = schedule_id.get('date_start') < schedule_vals.get('date_stop') <= schedule_id.get('date_stop')
        if condition_resource and (condition_date_start or condition_date_stop):
            return False
    return True


def calculate_time_in_minutes(date_stop, date_start):
    return int(((date_stop - date_start).seconds / 60))


def convert_hour_to_minute(hour):
    return (int(hour) * 60) or 0

