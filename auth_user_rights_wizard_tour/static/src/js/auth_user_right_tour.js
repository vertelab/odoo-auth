odoo.define('user_right.tour', function(require) {
    "use strict";

    var core = require('web.core');
    var tour = require('web_tour.tour');

    var _t = core._t;

    tour.register('user_right_tour', {
        url: "/web",
    },
    [
        tour.STEPS.SHOW_APPS_MENU_ITEM,
        {
            trigger: '.o_app[data-menu-xmlid="hr.menu_hr_root"]',
            content: _t('Click to <b>create employees</b>'),
            position: 'bottom',
            edition: 'community'
        },
        {
            trigger: ".o-kanban-button-new",
            content: _t("Click here to <b>create your first employee</b>."),
            position: "bottom",
        },
        {
            trigger: ".o_form_editable .o_field_char[name='name']",
            content: _t("<b>Enter a name</b> for the employee"),
            position: "right",
        },
        {
            trigger: "input[name=work_email]",
            content: _t("<b>Enter an email</b> for the employee\"."),
            position: "right",
            run: "text example@example.com",
        },
        {
            trigger: ".o_field_many2manytags[name='user_groups']",
            content: _t("<b>Assign group(s) to employee.</b>"),
            position: "right",
        },
        {
            trigger: ".o_form_button_save",
            content: _t("Once employee form is filled, you can save."),
            position: "bottom",
        }
    ]);

});


