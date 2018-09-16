/**
 * @author Nikos Oikonomou 
 * https://github.com/nikosoik/
 * 
 * StackSearch Javascript/jQuery backend.
 * 
 * Provides entity/tag utilities and the search mechanism.
 * 
 */

// Entities/Tags cookie handlers
function setCookie(cname, cvalue, exdays) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
    var expires = "expires=" + d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}

// Get cookie string or an empty string when the cookie is not present
function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) === ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) === 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

// Checks if value "val" exists
function duplicate(val, storedValArray) {
    if (storedValArray.indexOf(val) === -1) {
        return false
    }
    return true
}

// Creates a new entity/tag badge and stores value in cookie
function addEntities(valStr, cname, tagc, storedValArray) {
    if (valStr !== "") {
        var valArray = valStr.split(",").map(item => item.trim());

        for (i in valArray) {
            if (!duplicate(valArray[i], storedValArray)) {
                tagc.append("<span class='entity-tag btn-dark'>" +
                    valArray[i] + "<i class='fa fa-close'></i></span>");

                storedValArray.push(valArray[i]);
            }
        }
        setCookie(cname, JSON.stringify(storedValArray), 2);
    }
}

// Removes entity/tag badge and cookie stored value
function removeEntity(element, cname, storedValArray) {
    var eText = element.text();
    element.remove();
    storedValArray.splice($.inArray(eText, storedValArray), 1);
    setCookie(cname, JSON.stringify(storedValArray));
}

// Restores entities/tags and model info using cookie stored values
function restoreState(ecname, icname, tagc, modelInfo) {
    var entsCookie = getCookie(ecname);
    var infoCookie = getCookie(icname);
    var storedValArray = JSON.parse((entsCookie === "" ? "[]" : entsCookie));
    // restore badges
    if (storedValArray.length !== 0) {
        for (i in storedValArray) {
            tagc.append("<span class='entity-tag btn-dark'>" +
                storedValArray[i] + "<i class='fa fa-close'></i></span>");
        }
    }
    // restore model info
    if (infoCookie !== "") {
        modelInfo.text(infoCookie + " model")
    }
    return storedValArray;
}

function postFormData(query, tags) {
    var jdata = {
        "query": query,
        "tags": JSON.parse((tags === "" ? "[]" : tags))
    };

    $.ajax({
        url: "/search",
        type: "POST",
        data: JSON.stringify(jdata),
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        cache: false,
        success: function (response) {
            $("#content-panel").html(response["data"]);
        },
        error: function (jqXHR) {
            console.log(jqXHR);
        }
    });
}

$(function () {
    var $searchFormInputs = $("#search-form :input");
    var $tagContainer = $("#tag-container");
    var entsCookie = "ents";
    var infoCookie = "info";
    var storedEntities = restoreState(entsCookie, infoCookie, $tagContainer, $("#model-info"));

    /** 
     * Search mechanism functionality
     */

    // enter-keypress event: add new entities/tags, their badges and store value (cookie)
    $("#entity-input").keydown(function (event) {
        if (event.which === 13) {
            addEntities($(this).val().toLowerCase(),
                entsCookie, $tagContainer, storedEntities);
            $(this).val("");
        }
    });

    // button click event: add new entities/tags, their badges and store value (cookie)
    $("#btn-add-entity").click(function () {
        addEntities($("#entity-input").val().toLowerCase(),
            entsCookie, $tagContainer, storedEntities);
        $("#entity-input").val("");
    });

    // button 'x' event: remove tag and its stored cookie value
    $("#tag-container").on("click", ".entity-tag > .fa-close", function () {
        removeEntity($(this).parent(), entsCookie, storedEntities);
    });

    // enter-keypress event: post form data (query and tags)
    $("#query-input").keydown(function (event) {
        if (event.which === 13) {
            var query = $(this).val();
            var tags = getCookie(entsCookie);
            console.log(query);
            console.log(tags);
            $(this).val("");
            postFormData(query, tags);
        }
    });

    // button click event: post form data (query and tags)
    $("#btn-search").click(function () {
        var query = $("#query-input").val();
        var tags = getCookie(entsCookie);
        console.log(query);
        console.log(tags);
        $("#query-input").val("");
        postFormData(query, tags);
    });

    /**
     *  Model loading functionality
     */

    // button click event: send ajax request and wait for response
    // disable inputs until response
    // enable inputs after successful response
    $("#btn-load-model").click(function () {
        var $this = $(this);
        var $modelSelect = $("#model-select");

        $this.html("<i class='fa fa-spinner fa-fw fa-spin'></i>");
        $this.prop("disabled", true);
        $modelSelect.prop("disabled", true);
        $searchFormInputs.prop("disabled", true);
        $.getJSON("/load_model", {
            model_type: $("#model-select option:selected").text()
        }, function (response) {
            if (response["success"]) {
                console.log("Model loaded in memory: " + response["model"]);
                $searchFormInputs.prop("disabled", false);
                $("#model-info").text(response["model"] + " model");
                setCookie(infoCookie, response["model"], 2);
            } else {
                console.log(response["error"]);
                $("#model-info").text("Error loading model!");
            }
            $this.html("Load");
            $this.prop("disabled", false);
            $modelSelect.prop("disabled", false);
        });
    });
});