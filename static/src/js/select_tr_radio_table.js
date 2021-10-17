//----------------------SELECT SEVER PAKAGE------------------------
$('#tableSelect tr').click(function() {
    // ENABLE SELECT TR
    $(this).find('td div label input:radio').prop('checked', true);
    // GET PRICE VALUE
    // $("output").text($(this).find('td div label input:radio').val());
    var sum = parseFloat($(this).find('td div label input:radio').val());   
    $("output").html(sum.toLocaleString());
    // GET PRODUCT_ID
    $("#license_management_product_id").val($(this).find('td.d-none input').val());
})

// ONLOAD BODY BY JS
$( document ).ready(function() {
    // AUTO SELECT FIRST PACKAGE IN TABLE
    $('input[name="optradio"]').first().prop('checked', true)
    // AUTO GET FIRST PACKAGE's PRICE IN TABLE
    // $("output").text($(this).find('td div label input:radio').val());
    var sum = parseFloat($(this).find('td div label input:radio').val());   
    // $("output").html(sum.toLocaleString('vi', {style : 'currency', currency : 'VND'}));

  
    $("output").html(sum.toLocaleString());
   
    
    // GET PRODUCT_ID
    $("#license_management_product_id").val($(this).find('td.d-none input').val());
});

//----------------------SELECT PAYMENT PACKAGE------------------------
$('#tableSelectPaymentPackage tr').click(function() {
    // SELECT TR
    $(this).find('td div label input:radio').prop('checked', true);
})
// ONLOAD BODY BY JS
$(document).ready(function(){
    // AUTO SELECT FIRST PACKAGE IN TABLE
    $('input[name="optradio"]').first().prop('checked', true)
    // GET PAYMENT PACKAGE PRICE
    $('#tableSelectPaymentPackage tr').click(function(){
        var inputValue = $(this).find('td div label input:radio').attr('value');
        // CHAGE PRICE WHEN USER PAY THE BILL
        $("input[name='is_trial']").val(inputValue);
        // CHAGE PRICE WHEN USER CLICK PAYMENT PACKAGE
        var targetBox = $("." + inputValue);
        // only show right price (full or trial)
        $(".monetary_field").not(targetBox).hide();
        $(targetBox).show();
    });
});
