var correctCaptcha = function(response) {
    $("#recaptcha").val(response);
    $("#submit").removeAttr("disabled");
    $("#submit").click();
};

var onloadCallback = function() {
    grecaptcha.render('captcha', {
        'sitekey' : '6LfcU6QUAAAAAKZ5Cv2P6Rcu1il4-250zuLP9bPe',
        'callback' : correctCaptcha
    });
};