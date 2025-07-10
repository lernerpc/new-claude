/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SportPaymentDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            data: {},
            loading: true
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            const data = await this.orm.call(
                "sport.payment.dashboard",
                "get_dashboard_data",
                []
            );
            this.state.data = data;
            this.updateKPIs(data.kpis);
            this.updateTables(data.lists);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add("خطأ في تحميل البيانات", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    updateKPIs(kpis) {
        // Update KPI cards
        document.getElementById('total_students').textContent = kpis.total_students.toLocaleString();
        document.getElementById('paid_students').textContent = kpis.paid_students.toLocaleString();
        document.getElementById('unpaid_students').textContent = kpis.unpaid_students.toLocaleString();
        document.getElementById('total_revenue').textContent = kpis.total_revenue.toLocaleString();
        document.getElementById('payment_rate').textContent = `${kpis.payment_rate}% معدل الدفع`;
    }

    updateTables(lists) {
        // Update recent registrations table
        const recentTable = document.querySelector('#recentRegistrationsTable tbody');
        recentTable.innerHTML = '';
        lists.recent_registrations.forEach(registration => {
            const statusBadge = this.getStatusBadge(registration.payment_status);
            const row = `
                <tr>
                    <td>${registration.student_name}</td>
                    <td><small class="text-muted">${registration.registration_number}</small></td>
                    <td>${registration.registration_date}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
            recentTable.innerHTML += row;
        });

        // Update top sports table
        const sportsTable = document.querySelector('#topSportsTable tbody');
        sportsTable.innerHTML = '';
        lists.top_sports.forEach(sport => {
            const progressBar = this.getProgressBar(sport.payment_rate);
            const row = `
                <tr>
                    <td><strong>${sport.sport_name}</strong></td>
                    <td><span class="badge bg-primary">${sport.student_count}</span></td>
                    <td><span class="badge bg-success">${sport.paid_count}</span></td>
                    <td>
                        ${progressBar}
                        <small class="text-muted">${sport.payment_rate}%</small>
                    </td>
                </tr>
            `;
            sportsTable.innerHTML += row;
        });
    }

    getStatusBadge(status) {
        const statusMap = {
            'مدفوع': 'bg-success',
            'مدفوع جزئياً': 'bg-warning',
            'قيد الدفع': 'bg-info',
            'غير مدفوع': 'bg-danger'
        };
        const badgeClass = statusMap[status] || 'bg-secondary';
        return `<span class="badge ${badgeClass}">${status}</span>`;
    }

    getProgressBar(percentage) {
        const colorClass = percentage >= 80 ? 'bg-success' : 
                          percentage >= 60 ? 'bg-warning' : 'bg-danger';
        return `
            <div class="progress" style="height: 6px;">
                <div class="progress-bar ${colorClass}" style="width: ${percentage}%"></div>
            </div>
        `;
    }

    renderCharts() {
        if (!this.state.data.charts) return;

        // Payment Status Pie Chart
        this.renderPaymentStatusChart();
        
        // Sport Distribution Bar Chart
        this.renderSportDistributionChart();
        
        // Monthly Revenue Line Chart
        this.renderMonthlyRevenueChart();
    }

    renderPaymentStatusChart() {
        const ctx = document.getElementById('paymentStatusChart');
        if (!ctx) return;

        const data = this.state.data.charts.payment_status;
        const colors = ['#28a745', '#ffc107', '#17a2b8', '#dc3545'];
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(item => item.label),
                datasets: [{
                    data: data.map(item => item.value),
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 45
                        }
                    }
                }
            }
        });
    }

    renderMonthlyRevenueChart() {
        const ctx = document.getElementById('monthlyRevenueChart');
        if (!ctx) return;

        const data = this.state.data.charts.monthly_revenue;
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(item => item.label),
                datasets: [{
                    label: 'الإيرادات (جنيه)',
                    data: data.map(item => item.value),
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + ' ج.م';
                            }
                        }
                    }
                }
            }
        });
    }

    async refreshDashboard() {
        await this.loadDashboardData();
        this.renderCharts();
        this.notification.add("تم تحديث البيانات بنجاح", { type: "success" });
    }

    openDetailedReport() {
        this.action.doAction({
            name: "التقرير المفصل",
            type: "ir.actions.act_window",
            res_model: "student.sport.payment.report",
            view_mode: "tree",
            target: "current"
        });
    }

    openStudentAdmissions() {
        this.action.doAction({
            name: "تسجيلات الطلاب",
            type: "ir.actions.act_window",
            res_model: "student.admission",
            view_mode: "tree,form",
            target: "current"
        });
    }

    exportToExcel() {
        // Trigger export of the detailed report
        this.action.doAction({
            type: "ir.actions.act_url",
            url: "/web/export/xlsx?model=student.sport.payment.report&fields=[student_name,activity_name,membership_number,membership_month,payment_memo,payment_state]",
            target: "new"
        });
    }
}

SportPaymentDashboard.template = "sport_payment_dashboard_template";

// Register the component
registry.category("actions").add("sport_payment_dashboard", SportPaymentDashboard);

// Global functions for button clicks
window.viewAllRegistrations = function() {
    window.location.href = "/web#action=student_admission_action&model=student.admission&view_type=list";
};

window.openDetailedReport = function() {
    window.location.href = "/web#action=action_student_sport_payment_report&model=student.sport.payment.report&view_type=list";
};

window.exportToExcel = function() {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/web/export/xlsx';
    form.target = '_blank';
    
    const fields = [
        'student_name', 'activity_name', 'membership_number', 
        'membership_month', 'payment_memo', 'payment_state'
    ];
    
    const modelInput = document.createElement('input');
    modelInput.type = 'hidden';
    modelInput.name = 'model';
    modelInput.value = 'student.sport.payment.report';
    form.appendChild(modelInput);
    
    const fieldsInput = document.createElement('input');
    fieldsInput.type = 'hidden';
    fieldsInput.name = 'fields';
    fieldsInput.value = JSON.stringify(fields);
    form.appendChild(fieldsInput);
    
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
};

window.openStudentAdmissions = function() {
    window.location.href = "/web#action=action_student_admission&model=student.admission&view_type=list";
};d: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }

    renderSportDistributionChart() {
        const ctx = document.getElementById('sportDistributionChart');
        if (!ctx) return;

        const data = this.state.data.charts.sport_distribution;
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(item => item.label),
                datasets: [{
                    label: 'عدد الطلاب',
                    data: data.map(item => item.value),
                    backgroundColor: '#007bff',
                    borderColor: '#0056b3',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legen
