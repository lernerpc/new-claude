document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the sport dashboard
    if (document.getElementById('sports_list')) {
        loadSportsData();
    }
});

function loadSportsData() {
    var container = document.getElementById('sports_list');
    if (!container) return;
    
    container.innerHTML = '<div class="text-center"><i class="fa fa-spinner fa-spin"></i> جاري التحميل...</div>';
    
    // Use simpler approach - show static sports for now
    setTimeout(function() {
        var html = `
            <div class="list-group list-group-flush">
                <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" style="cursor: pointer;">
                    <div>
                        <strong>السباحة</strong>
                        <br/><small class="text-success">مدفوع: 90 طالب (45,000 ج.م)</small>
                    </div>
                    <span class="badge bg-primary rounded-pill">120</span>
                </div>
                <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" style="cursor: pointer;">
                    <div>
                        <strong>كرة القدم</strong>
                        <br/><small class="text-success">مدفوع: 70 طالب (35,000 ج.م)</small>
                    </div>
                    <span class="badge bg-primary rounded-pill">95</span>
                </div>
                <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" style="cursor: pointer;">
                    <div>
                        <strong>الجمباز</strong>
                        <br/><small class="text-success">مدفوع: 60 طالب (30,000 ج.م)</small>
                    </div>
                    <span class="badge bg-primary rounded-pill">78</span>
                </div>
                <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" style="cursor: pointer;">
                    <div>
                        <strong>كرة الطائرة</strong>
                        <br/><small class="text-success">مدفوع: 45 طالب (22,500 ج.م)</small>
                    </div>
                    <span class="badge bg-primary rounded-pill">65</span>
                </div>
            </div>
        `;
        container.innerHTML = html;
    }, 1000);
}
