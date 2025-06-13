/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";

export class CustomDashBoard extends Component {
    static template = "bi_sport_parent_management.ParentDashboard";
    
    setup() {
        this.state = useState({
            total_parents: 0
        });
        this.orm = this.env.services.orm;
        this.action = this.env.services.action;

        onWillStart(async () => {
            try {
                const data = await this.orm.call("res.partner", "get_data", []);
                if (data && typeof data === 'object') {
                    this.state.total_parents = data.total_parents || 0;
                }
            } catch (error) {
                console.error("Error loading dashboard data:", error);
                this.env.services.notification.add("Error loading dashboard data", {
                    type: "danger",
                });
            }
        });
    }

    async viewParents(ev) {
        try {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Parents",
                res_model: "res.partner",
                domain: [["is_parent", "=", true]],
                views: [[false, "kanban"], [false, "tree"], [false, "form"]],
                target: "current",
            });
        } catch (error) {
            console.error("Error opening parents view:", error);
            this.env.services.notification.add("Error opening parents view", {
                type: "danger",
            });
        }
    }
}

registry.category("actions").add("bi_sport_parent_management.dashboard_action", CustomDashBoard);
