var website = openerp.website;
var lang = $("html").attr("lang");




var strength = {
        0: "Worst ☹",
        1: "Bad ☹",
        2: "Weak ☹",
        3: "Good ☺",
        4: "Strong ☻"
}

var password = document.getElementById('password');
var meter = document.getElementById('password-strength-meter');
var text = document.getElementById('password-strength-text');

password.addEventListener('input', function()
{
    var val = password.value;
    var result = zxcvbn(val);
    
    // Update the password strength meter
    meter.value = result.score;
   
    // Update the text indicator
    if(val !== "") {
        text.innerHTML = "Strength: " + "<strong>" + strength[result.score] + "</strong>" + "<span class='feedback'>" + result.feedback.warning + " " + result.feedback.suggestions + "</span"; 
    }
    else {
        text.innerHTML = "";
    }
});



    //~ $(oe_website_sale).on("change", 'input[name="password"]', function (event) {
            //~ var $pw_dom = $(this).closest("form");
            //~ openerp.jsonRpc("/auth_pwcheck", 'call', {'passwd': $pw_dom.find('input[name="password"]').val()})
            //~ .then(function (data) {
                //~ var current = $product_dom.data("attribute_value_ids");
                //~ for(var j=0; j < current.length; j++){
                    //~ current[j][2] = data[current[j][0]];
                //~ }
                //~ $product_dom.attr("data-attribute_value_ids", JSON.stringify(current)).trigger("change");
            //~ });
        //~ });


