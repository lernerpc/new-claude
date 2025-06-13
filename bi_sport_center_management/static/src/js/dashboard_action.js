/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Component ,onMounted} from "@odoo/owl";
import {  useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render"; 
export class CustomDashBoard extends Component {
   
   
        static template= 'CenterDashboard'
        static props = ["*"];
      

        setup() {
            super.setup();
            this.user = useService("user")
            this.action = useService("action");
            this.orm = useService("orm");
            this.state = useState({
                dashboards_templates: ['CenterDashboard'],
                templates: [],
                total_bookings : 0,
                total_inquiries : 0,
                total_equipment : 0,
                total_students : 0,
                total_trainers : 0,
                total_center_spaces : 0, 
                total_center_events : 0,
                total_sports : 0,
              
            }) 
            
        
            onMounted(async () => {
                    var self = this;
                    await self.fetch_data()              
            });    
            }
     

        init () {
            super.init(...arguments);
            this.dashboards_templates = ['CenterDashboard'];
            this.orm = this.bindService("orm");
        }
 
    
        render_dashboards() {
            var self = this;
            _.each(this.dashboards_templates, function(template) {
                self.$('.o_dashboard').append(renderToElement(template, { widget: self }));
            });
        }
    
  
        async fetch_data()  {
            var self = this;
            var def1 = await this.orm.call('res.partner', 'get_data')                
            self.state.total_bookings = def1['total_bookings']
            self.state.total_inquiries = def1['total_inquiries']
            self.state.total_equipment = def1['total_equipment']
            self.state.total_students = def1['total_students']
            self.state.total_trainers = def1['total_trainers']
            self.state.total_center_spaces = def1['total_center_spaces']
            self.state.total_center_events = def1['total_center_events']
            self.state.total_sports = def1['total_sports']
            self.state.total_confirm_admissions = def1['total_confirm_admissions']
            return def1 

        }
 
        //Total Student action
        tot_students(e) {
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.action.doAction({
                name: _t("Students"),
                type: 'ir.actions.act_window',
                res_model: 'res.partner',
                view_mode: 'tree,form,calendar',
                views: [
                    [false, 'list'],
                    [false, 'form']
                ],
                domain: [
                    ['is_student', '=', true]
                ],
                target: 'current',
                context: { 'default_is_student': true }
            }, options)
        }
        //Total Inquiries action
        tot_inquiries(e) {
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.action.doAction({
                name: _t("Inquiries"),
                type: 'ir.actions.act_window',
                res_model: 'student.inquiry',
                view_mode: 'tree,form',
                views: [
                    [false, 'list'],
                    [false, 'form']
                ],
                domain: [
                    ['state', '=', 'new']
                ],
                target: 'current',
            }, options)
        }
        //Total Trainers action
        tot_trainers(e) {
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.action.doAction({
                name: _t("Trainers"),
                type: 'ir.actions.act_window',
                res_model: 'res.partner',
                view_mode: 'tree,form',
                views: [
                    [false, 'list'],
                    [false, 'form']
                ],
                domain: [
                    ['is_coach', '=', true]
                ],
                context: { 'default_is_coach': true },
                target: 'current'
            }, options)
        }
        //Total Equipemnts action
        tot_equipment(e) {
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.action.doAction({
                name: _t("Equipment"),
                type: 'ir.actions.act_window',
                res_model: 'product.product',
                view_mode: 'tree,form',
                views: [
                    [false, 'list'],
                    [false, 'form']
                ],
                domain: [
                    ['is_equipment', '=', true]
                ],
                context: { 'default_is_equipment': true },
                target: 'current'
            }, options)
        }
        //Total Admissions action
        tot_admissions(e) {
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.action.doAction({
                name: _t("Trainers"),
                type: 'ir.actions.act_window',
                res_model: 'student.admission',
                view_mode: 'tree,form',
                views: [
                    [false, 'list'],
                    [false, 'form']
                ],
                context: { 'default_is_coach': true },
                target: 'current'
            }, options)
        }
        //total grounds space open
        tot_grounds(e) {
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.action.doAction({
                name: _t("Center Space Ground"),
                type: 'ir.actions.act_window',
                res_model: 'product.product',
                view_mode: 'kanban,tree,form',
                views: [
                    [false, 'kanban'],
                    [false, 'list'],
                    [false, 'form']
                ],
                domain: [
                    ['is_space', '=', true]
                ],
                context: { 'default_is_space': true },
                target: 'current'
            }, options)
        }
        //total grounds space open
        tot_booking(e) {
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.action.doAction({
                name: _t("Bookings"),
                type: 'ir.actions.act_window',
                res_model: 'center.booking',
                view_mode: 'tree,form',
                views: [
                    [false, 'list'],
                    [false, 'form']
                ],
                target: 'current'
            }, options)
        }
        //total Sports open
        tot_sports(e) {
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.action.doAction({
                name: _t("Center Sports Activity"),
                type: 'ir.actions.act_window',
                res_model: 'res.partner',
                view_mode: 'kanban,tree,form',
                views: [
                    [false, 'kanban'],
                    [false, 'list'],
                    [false, 'form']
                ],
                domain: [
                    ['is_sport', '=', true]
                ],
                target: 'current',
                context: { 'default_is_sport': true },
            }, options)
        }
        //available events
        avai_events(e) {
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.action.doAction({
                name: _t("Current events"),
                type: 'ir.actions.act_window',
                res_model: 'event.event',
                view_mode: 'tree,form',
                views: [
                    [false, 'kanban'],
                    [false, 'list'],
                    [false, 'form']
                ],
                target: 'current'
            }, options)
        } 
    }

    registry.category("actions").add("coworking_space_dashboard_tag", CustomDashBoard);
