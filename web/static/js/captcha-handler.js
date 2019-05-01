var correctCaptcha = function(response) {
    $("form").attr("action", $("form").attr("action")+"?g-recaptcha-response="+response);
    $("#submit").removeAttr("disabled");
    $("#submit").click();
};

var onloadCallback = function() {
    grecaptcha.render('captcha', {
        'sitekey' : '6LfthEQUAAAAAPUBIJyG1jTHZhipxk_CUhzUGejR',
        'callback' : correctCaptcha
    });
};