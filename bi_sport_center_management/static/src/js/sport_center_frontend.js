/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";
    publicWidget.registry.SporCenterManagement = publicWidget.Widget.extend({
        selector: '#registration_create_form',
        events: {
            "click .is_disability": "_onClick_is_disability",
        },

        init: function(parent) {
            this._super(parent);
            $('.disability_description').hide()
           
        },
        _onClick_is_disability: function() {
            $('#disability_description').removeClass('d-none');
            var Is_DisabilityBool = document.getElementById("is_disability");
            Is_DisabilityBool.addEventListener("change", function() {
                if (Is_DisabilityBool.checked) {
                    $('#disability_description').removeClass('d-none');
                } else {
                    $('#disability_description').addClass('d-none');
                }
            });
        },
    })

    publicWidget.registry.BookGroundCenter = publicWidget.Widget.extend({
        selector: '#booking_create_form',
        events: {
            "click #submit_booking_check": "_onSubmit_book_check",
            'change #ground_id': '_onGroundChange',
        },
        init: function(parent) {
            this._super(parent);
            this.rpc = this.bindService("rpc");
        },

        _onSubmit_book_check: function() {
            var data = $('#book_check_record').serializeArray();
            var start_date = data[0].value;
            var end_date = data[1].value;
            var ground_id = data[2].value;
            var sportname_id = data[3].value;
            const today = new Date().toISOString().split('.')[0];
            const dateTimeParts = today.split(':');
            const datePart = dateTimeParts[0] + ':' + dateTimeParts[1];

            if (start_date == '' || end_date == '' || ground_id == '' || sportname_id == '') {
                alert('Please fill all the values!');
            } else if (start_date < datePart) {
                alert('Please fill right time value!');
            } else if (end_date < start_date) {
                alert('Please make proper date format!');
            } else {
                var data = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'ground_id': ground_id,
                    'sportname_id': sportname_id,
                }
            jsonrpc('/check_book/availability', data ,{
                    args: [],
                    kwargs: {}
                }).then(function(result) {         
                    if (result.status == 'available') {
                            $('#model_start_date').val(start_date).prop('readonly', true);
                            $('#model_end_date').val(end_date).prop('readonly', true);
                            $('#model_ground_id').val(ground_id).prop('readonly', true);
                            $('#model_sportname_id').val(sportname_id).prop('readonly', true);
                            $('#model_user_name').val(result.user).prop('readonly', true);
                            $('#model_user_email').val(result.email).prop('readonly', true);
                            $('#model_user_mobile').val(result.mobile);
                            $('#model_user_id').val(result.id).prop('readonly', true);
                            $('#check_validate_model').modal('show');
                        } else {
                            alert("Slot not available! \nPlease select another time or ground.")
                        }
                    });
                
            }
        },

        _onGroundChange:async function(ev) {
            var self = this;
            var groundId = $(ev.currentTarget).val();
            await this.rpc('/get_sports',{ ground_id: groundId},
            ).then(function(sports) {
                var $sportSelect = self.$el.find('#sportname_id');
                $sportSelect.empty();
                $sportSelect.append('<option value="" label="Select Sport">Select Sport</option>');
                sports.forEach((sport) => {
                    $sportSelect.append('<option value="' + sport.id + '">' + sport.name + '</option>');
                });
            });
        },
    });
    


$("#closeBtn").on('click', function() {
    $('#check_validate_model').modal('hide');
});

$( "#datetimepicker_start_date" ).on( "click", function( event ) {
    $('#datetimepicker_start_date').datetimepicker(event);
  });
$( "#datetimepicker_end_date" ).on( "click", function( event ) {
    $('#datetimepicker_end_date').datetimepicker(event);
  });

