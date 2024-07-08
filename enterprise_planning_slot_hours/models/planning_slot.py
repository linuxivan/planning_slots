# Copyright 2024 Coninpe ((https://coninpe.es).)
# Ivan Perez <iperez@coninpe.ez>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.osv import expression


def float_to_time_string(hour_float):
    # Extraer la parte entera (horas) y la parte decimal (minutos)
    hours = int(hour_float)
    minutes = int((hour_float - hours) * 60)

    # Formatear las horas y minutos con dos dígitos
    time_string = f"{hours:02}:{minutes:02}"
    return time_string


class PlanningSlot(models.Model):
    _inherit = "planning.slot"

    task_effective_hours = fields.Float(
        string="Effective hours",
        compute="_compute_task_effective_hours",
        compute_sudo=True,
        store=True,
    )

    def name_get(self):
        group_by = self.env.context.get('group_by', [])
        # Sudo as a planning manager is not able to read private project if he is not project manager.
        self = self.sudo()
        result = []
        for slot in self:
            if 'task_id' in group_by:
                if len(slot.resource_id) > 0:
                    if slot.task_id:
                        name = float_to_time_string(slot.allocated_hours) + "PH" + " / " + float_to_time_string(
                            slot.task_effective_hours) + "EH"
                    else:
                        name = float_to_time_string(slot.allocated_hours) + "PH" + " / " + float_to_time_string(
                            slot.effective_hours) + "EH"
                    result.append([slot.id, name or ''])
                else:
                    name = slot.project_id.name + " / " + (
                        slot.task_id.name if slot.task_id else "No Task") + " / " + float_to_time_string(
                        slot.allocated_hours)
                    result.append([slot.id, name or ''])
            else:
                if len(slot.resource_id) > 0:
                    if slot.task_id:
                        name = slot.project_id.name + " / " + (
                            slot.task_id.name if slot.task_id else "No Task") + float_to_time_string(
                            slot.allocated_hours) + "PH" + " / " + float_to_time_string(
                            slot.task_effective_hours) + "EH"
                    else:
                        name = slot.project_id.name + " / " + float_to_time_string(
                            slot.allocated_hours) + "PH" + " / " + float_to_time_string(
                            slot.effective_hours) + "EH"
                    result.append([slot.id, name or ''])
                else:
                    name = slot.project_id.name + " / " + (
                        slot.task_id.name if slot.task_id else "No Task") + " / " + float_to_time_string(
                        slot.allocated_hours)
                    result.append([slot.id, name or ''])
        return result

    def _get_task_timesheet_domain(self):
        '''
        Returns the domain used to fetch the timesheets, None is returned in case there would be no match
        '''
        self.ensure_one
        if not self.project_id:
            return None
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.start_datetime.date()),
            ('date', '<=', self.end_datetime.date()),
            ('task_id', '=', self.task_id.id),
        ]
        if self.project_id:
            domain = expression.AND([[('account_id', '=', self.project_id.analytic_account_id.id)], domain])
        return domain

    @api.depends('employee_id', 'start_datetime', 'end_datetime', 'project_id.analytic_account_id',
                 'project_id.analytic_account_id.line_ids', 'project_id.analytic_account_id.line_ids.unit_amount')
    def _compute_task_effective_hours(self):
        Timesheet = self.env['account.analytic.line']
        for forecast in self:
            if not forecast.task_id:
                forecast.task_effective_hours = 0
                return
            if not forecast.project_id or not forecast.start_datetime or not forecast.end_datetime:
                forecast.task_effective_hours = 0
                forecast.timesheet_ids = False
            else:
                domain = forecast._get_task_timesheet_domain()
                if domain:
                    timesheets = Timesheet.search(domain)
                else:
                    timesheets = Timesheet.browse()

                forecast.task_effective_hours = sum(timesheet.unit_amount for timesheet in timesheets)
                forecast.timesheet_ids = timesheets
