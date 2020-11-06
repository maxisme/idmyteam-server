$(function(){
	$('#alert-close').click(function(){
		$( "#alert-box" ).fadeOut("slow");
	});

	/* materialize stuff */
	$(".button-collapse").sideNav();
	$('select').material_select();
	$('.modal').modal();

    function fadeInOut() {
        var el = $(".flashme");
        el.animate({opacity:'0.2'}, 1000);
        el.animate({opacity:'1'}, 1000, fadeInOut);
    }
    fadeInOut();
});
