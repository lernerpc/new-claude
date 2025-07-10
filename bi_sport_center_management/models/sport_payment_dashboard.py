# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, tools, api


class SportPaymentDashboard(models.Model):
    _name = 'sport.payment.dashboard'
    _description = 'Sport Payment Dashboard'
    _auto = False

    # Dashboard fields
    name = fields.Char(string='Dashboard', default='Sport Payment Dashboard')
    total_students = fields.Integer(string='Total Students', compute='_compute_dashboard_data', store=False)
    paid_students = fields.Integer(string='Paid Students', compute='_compute_dashboard_data', store=False)
    unpaid_students = fields.Integer(string='Unpaid Students', compute='_compute_dashboard_data', store=False)
    total_revenue = fields.Float(string='Total Revenue', compute='_compute_dashboard_data', store=False)
    paid_revenue = fields.Float(string='Paid Revenue', compute='_compute_dashboard_data', store=False)
    unpaid_revenue = fields.Float(string='Unpaid Revenue', compute='_compute_dashboard_data', store=False)
    payment_rate = fields.Float(string='Payment Rate', compute='_compute_dashboard_data', store=False)
    
    # Selected sport for filtering - stored in context
    selected_sport_id = fields.Integer(string='Selected Sport ID', default=0, store=False)
    selected_sport_name = fields.Char(string='Selected Sport Name', default='جميع الرياضات', store=False)

    def init(self):
        """Initialize dashboard view"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    1 as id,
                    'Sport Payment Dashboard' as name
            )
        ''' % self._table)

    @api.depends()
    def _compute_dashboard_data(self):
        """Compute dashboard statistics with sport filter"""
        for record in self:
            # Get selected sport from context
            selected_sport_id = self.env.context.get('selected_sport_id', 0)
            selected_sport_name = self.env.context.get('selected_sport_name', 'جميع الرياضات')
            
            record.selected_sport_id = selected_sport_id
            record.selected_sport_name = selected_sport_name
            
            if selected_sport_id:
                # When sport is selected, count only students with that sport
                self.env.cr.execute(f"""
                    SELECT 
                        COUNT(DISTINCT sa.student_id) as total_students,
                        COUNT(DISTINCT CASE 
                            WHEN latest_invoice.payment_state = 'paid' THEN sa.student_id 
                        END) as paid_students,
                        COUNT(DISTINCT CASE 
                            WHEN latest_invoice.payment_state != 'paid' OR latest_invoice.invoice_id IS NULL THEN sa.student_id 
                        END) as unpaid_students,
                        COALESCE(SUM(CASE 
                            WHEN latest_invoice.payment_state = 'paid' THEN latest_invoice.amount_total 
                        END), 0) as paid_revenue,
                        COALESCE(SUM(CASE 
                            WHEN latest_invoice.payment_state != 'paid' AND latest_invoice.amount_total IS NOT NULL THEN latest_invoice.amount_total 
                        END), 0) as unpaid_revenue,
                        COALESCE(SUM(latest_invoice.amount_total), 0) as total_revenue
                    FROM student_admission sa
                    JOIN product_product_student_admission_rel rel ON rel.student_admission_id = sa.id
                    JOIN product_product pp ON rel.product_product_id = pp.id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    LEFT JOIN LATERAL (
                        SELECT 
                            am.id as invoice_id,
                            am.payment_state,
                            am.amount_total
                        FROM account_move am
                        WHERE am.invoice_origin = sa.name
                            AND am.move_type = 'out_invoice'
                            AND am.state = 'posted'
                        ORDER BY am.invoice_date DESC, am.id DESC
                        LIMIT 1
                    ) latest_invoice ON TRUE
                    WHERE sa.state IN ('enrolled', 'student')
                        AND pt.is_sportname = true
                        AND pp.id = {selected_sport_id}
                """)
            else:
                # When no sport selected, count ALL students (including those without sports)
                self.env.cr.execute("""
                    SELECT 
                        COUNT(DISTINCT sa.student_id) as total_students,
                        COUNT(DISTINCT CASE 
                            WHEN latest_invoice.payment_state = 'paid' THEN sa.student_id 
                        END) as paid_students,
                        COUNT(DISTINCT CASE 
                            WHEN latest_invoice.payment_state != 'paid' OR latest_invoice.invoice_id IS NULL THEN sa.student_id 
                        END) as unpaid_students,
                        COALESCE(SUM(CASE 
                            WHEN latest_invoice.payment_state = 'paid' THEN latest_invoice.amount_total 
                        END), 0) as paid_revenue,
                        COALESCE(SUM(CASE 
                            WHEN latest_invoice.payment_state != 'paid' AND latest_invoice.amount_total IS NOT NULL THEN latest_invoice.amount_total 
                        END), 0) as unpaid_revenue,
                        COALESCE(SUM(latest_invoice.amount_total), 0) as total_revenue
                    FROM student_admission sa
                    LEFT JOIN LATERAL (
                        SELECT 
                            am.id as invoice_id,
                            am.payment_state,
                            am.amount_total
                        FROM account_move am
                        WHERE am.invoice_origin = sa.name
                            AND am.move_type = 'out_invoice'
                            AND am.state = 'posted'
                        ORDER BY am.invoice_date DESC, am.id DESC
                        LIMIT 1
                    ) latest_invoice ON TRUE
                    WHERE sa.state IN ('enrolled', 'student')
                """)
            
            result = self.env.cr.fetchone()
            total_students = result[0] or 0
            paid_students = result[1] or 0
            unpaid_students = result[2] or 0
            paid_revenue = result[3] or 0
            unpaid_revenue = result[4] or 0
            total_revenue = result[5] or 0
            
            record.total_students = total_students
            record.paid_students = paid_students
            record.unpaid_students = unpaid_students
            record.paid_revenue = paid_revenue
            record.unpaid_revenue = unpaid_revenue
            record.total_revenue = total_revenue
            record.payment_rate = round((paid_students / total_students * 100) if total_students > 0 else 0, 1)

    def get_all_sports_with_revenue(self):
        """Get ALL sports with student count and revenue - open wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'اختر رياضة للفلترة',
            'res_model': 'sport.selection.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def clear_sport_filter(self):
        """Clear sport filter"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'لوحة التحكم المتقدمة',
            'res_model': 'sport.payment.dashboard',
            'view_mode': 'form',
            'target': 'current',
            'res_id': 1,
            'context': {}
        }

    def open_detailed_report(self):
        """Open the detailed sport payment report with current sport filter"""
        selected_sport_id = self.env.context.get('selected_sport_id', 0)
        selected_sport_name = self.env.context.get('selected_sport_name', 'جميع الرياضات')
        
        domain = []
        if selected_sport_id:
            domain.append(('activity_id', '=', selected_sport_id))
            
        return {
            'name': f'التقرير المفصل - {selected_sport_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'student.sport.payment.report',
            'view_mode': 'tree',
            'target': 'current',
            'domain': domain,
        }

    def open_student_admissions(self):
        """Open student admissions with current sport filter"""
        selected_sport_id = self.env.context.get('selected_sport_id', 0)
        selected_sport_name = self.env.context.get('selected_sport_name', 'جميع الرياضات')
        
        domain = [('state', 'in', ['enrolled', 'student'])]
        
        if selected_sport_id:
            domain.append(('activity_ids', 'in', [selected_sport_id]))
            
        return {
            'name': f'تسجيلات الطلاب - {selected_sport_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'student.admission',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': domain,
        }
