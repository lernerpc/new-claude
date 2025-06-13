/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";

export class SportDashboard extends Component {
    static template = "bi_sport_parent_management.CenterDashboard";
    setup() {
        this.state = useState({
            total_inquiries: 0,
            total_students: 0,
            total_trainers: 0,
            total_center_events: 0,
            total_center_spaces: 0,
            total_sports: 0,
            total_bookings: 0,
            total_confirm_admissions: 0,
            total_equipment: 0,
        });
        this.orm = this.env.services.orm;
        this.action = this.env.services.action;

        onWillStart(async () => {
            try {
                console.log("Fetching dashboard data...");
                const data = await this.orm.call("sport.dashboard", "get_dashboard_data", []);
                console.log("Dashboard data received:", data);
                Object.assign(this.state, data);
            } catch (error) {
                console.error("Failed to load dashboard data:", error);
                this.env.services.notification.add("Error loading dashboard data: " + error.message, {
                    type: "danger",
                });
            }
        });
    }

    async tot_inquiries() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Inquiries",
            res_model: "student.inquiry",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async tot_students() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Students",
            res_model: "res.partner",
            domain: [['is_student', '=', true]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async tot_trainers() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Coaches",
            res_model: "res.partner",
            domain: [['is_coach', '=', true]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async avai_events() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Events",
            res_model: "event.event",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async tot_grounds() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Grounds",
            res_model: "product.product",
            domain: [['is_space', '=', true]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async tot_sports() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Sports",
            res_model: "product.product",
            domain: [['is_sportname', '=', true]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async tot_booking() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Bookings",
            res_model: "center.booking",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async tot_admissions() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Registrations",
            res_model: "student.admission",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async tot_equipment() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Equipment",
            res_model: "product.product",
            domain: [['is_equipment', '=', true]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("bi_sport_parent_management.dashboard", SportDashboard);
