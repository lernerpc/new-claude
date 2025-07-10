# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SportSelectionWizard(models.TransientModel):
    _name = 'sport.selection.wizard'
    _description = 'Sport Selection Wizard'

    @api.model  
    def default_sports_list(self):
        """Get default sports list"""
        try:
            self.env.cr.execute("""
                SELECT 
                    pp.id as sport_id,
                    CASE
                        WHEN pt.name::text LIKE '%%{%%' THEN
                            COALESCE(
                                pt.name::json->>'en_US',
                                pt.name::json->>'ar_SY',
                                pt.name::text
                            )
                        ELSE pt.name::text
                    END as sport_name,
                    COUNT(DISTINCT sa.student_id) as student_count,
                    COALESCE(SUM(CASE 
                        WHEN latest_invoice.payment_state = 'paid' THEN latest_invoice.amount_total 
                    END), 0) as paid_revenue
                FROM student_admission sa
                JOIN product_product_student_admission_rel rel ON rel.student_admission_id = sa.id
                JOIN product_product pp ON rel.product_product_id = pp.id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN LATERAL (
                    SELECT 
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
                GROUP BY pp.id, sport_name
                ORDER BY student_count DESC
            """)
            
            sports_data = self.env.cr.fetchall()
            return [(str(sport[0]), f"{sport[1]} ({sport[2]} طالب - {sport[3]:,.0f} ج.م)") for sport in sports_data]
        except:
            return []

    sport_id = fields.Selection(selection='default_sports_list', string='اختر الرياضة', required=True)

    def select_sport(self):
        """Select sport and return to dashboard"""
        if not self.sport_id:
            return
            
        # Find sport name from the selection
        sport_options = dict(self.default_sports_list())
        sport_display = sport_options.get(self.sport_id, 'رياضة مختارة')
        sport_name = sport_display.split(' (')[0]  # Extract just the name
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'لوحة التحكم المتقدمة - {sport_name}',
            'res_model': 'sport.payment.dashboard',
            'view_mode': 'form',
            'target': 'current',
            'res_id': 1,
            'context': {
                'selected_sport_id': int(self.sport_id),
                'selected_sport_name': sport_name
            }
        }
