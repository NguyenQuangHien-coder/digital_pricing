$(document).on("click", ".open-UpgradePackage", function () {
    var value = $(this).data('package-id');
    $("input[name='package_id']").val(value)
});
