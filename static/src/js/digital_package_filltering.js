//----------------------SELECT DIGITAL PACKAGE------------------------
// ONLOAD BODY BY JS
$(document).ready(function(){
    // AUTO SELECT FISRT LABEL
    $('input[name="digital_package"]').first().prop('checked', true)
    // HIGHLIGHT FIRST LABEL
    $('input[name="digital_package"]').first().next('span').addClass('highlight_digital_package');
    // AUTO SELECT PRODUCTS HAVE LOWEST package_id, must create Starter in product.digitalpackage.value first
    var ids = $('#digital_package_grid >div').map(function() {
        // return $(this).attr('value');
        return $(this).data('package-seq');
    }).get();
    var lowest = Math.min.apply( Math, ids );
    
    $('#digital_package_grid >div').hide();      
    $('#digital_package_grid >div').filter(function () {
        // var v = $(this).attr('value');
        var v = $(this).data('package-seq');
        return v == lowest;
    }).show();
    
    // CLICK FUNTION
    // FILLTER BY VALUE (package_id)
    $('input[name="digital_package"]').click(function () {
        var value = $(this).attr('value');
        $('#digital_package_grid >div').hide();      
        
        if (value) {
            $('#digital_package_grid >div').filter(function () {
                var v = $(this).attr('value');
                return  value == v ;
            }).show();
        }  
    });

    // HIGHLIGHT SELECTED RADIO
    $("input[name='digital_package']").on('change', function(e) {
        $("input[name='digital_package']").removeClass('myClass');
       $("input[name='digital_package']").next('span').removeClass('highlight_digital_package');
       if($(this).is(':checked')) {
              $(this).addClass('myClass');
           $(this).next('span').addClass('highlight_digital_package');
       }
     });
});

