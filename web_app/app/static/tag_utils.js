$(function () {
    function setCookie(cname, cvalue, exdays) {
        var d = new Date();
        d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
        var expires = "expires=" + d.toUTCString();
        document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
    }

    function getCookie(cname) {
        var name = cname + "=";
        var ca = document.cookie.split(';');
        for (var i = 0; i < ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0) == ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) == 0) {
                return c.substring(name.length, c.length);
            }
        }
        return "";
    }
    // Checks if value "val" exists already
    function duplicate(val, oldVal) {
        var oldValArray = oldVal.split(",");
        // remove first empty item
        oldValArray.shift();
        // check if in array
        if (oldValArray.indexOf(val) == -1) {
            return false
        }
        return true
    }
    /* Creates a new entity tag and appends value in
       the hidden input */
    function addEntities(valStr, cname, tc) {
        var valArray = valStr.split(",").map(item => item.trim());
        var oldValStr = getCookie(cname);
        var newValStr = oldValStr;
        for (i in valArray) {
            if (!duplicate(valArray[i], oldValStr)) {
                tc.append("<span class='entity-tag btn-dark'>" +
                    valArray[i] + "<i class='fa fa-close'></i></span>");

                newValStr = newValStr + "," + valArray[i];
            }
        }
        setCookie(cname, newValStr, 2);
    }

    function removeEntity(element, cname) {
        var eText = element.text();
        element.remove();
        var oldValStr = getCookie(cname);
        var newValStr = oldValStr.replace(new RegExp("," + eText), "");
        setCookie(cname, newValStr);
    }

    function restoreEntities(cname, tc, hi) {
        var valStr = getCookie(cname);
        if (valStr != "") {
            var valArray = valStr.split(",");
            for (var i = 1; i < valArray.length; i++) {
                tc.append("<span class='entity-tag btn-dark'>" +
                    valArray[i] + "<i class='fa fa-close'></i></span>");
            }
        }
    }

    var tagContainer = $("#tag-container");
    var localCookie = "tags";
    restoreEntities(localCookie, tagContainer);

    /* On enter keypress or button click parse entities 
       (split on comma etc.) and add them */
    $("#entity-input").keydown(function (event) {
        if (event.which == 13) {
            addEntities($(this).val().toLowerCase(),
                localCookie, tagContainer);
            $(this).val("");
        }
    });

    $("#btn-add-entity").click(function () {
        addEntities($("#entity-input").val().toLowerCase(),
            localCookie, tagContainer);
        $("#entity-input").val("");
    });

    $("#tag-container").on("click", ".entity-tag > .fa-close", function () {
        removeEntity($(this).parent(), localCookie);
    });
});