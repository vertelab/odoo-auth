var website = openerp.website;
var lang = $("html").attr("lang");

$(document).ready(function() {

    var $password = $("#password");
    var $meter = $("#password-strength-meter");
    var $score_text = $("#password-strength-score");
    var $text = $("#password-strength-text");

    $password.on('keyup input', function (event){
        //~ var $pw_dom = $password.closest("form");
        openerp.jsonRpc("/auth_pwcheck", "call", {"passwd": $password.val()})
        .then(function (data) {
            $meter.val(data["score"]);
            $score_text.text(data['score_text']);
            $text.text(data['feedback']);
        });
    });
});
