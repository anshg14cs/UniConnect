const featureSteps =
    document.querySelectorAll(".feature-step");

const previewPanels =
    document.querySelectorAll(".preview-panel");

const progressDots =
    document.querySelectorAll(".progress-dot");


function activateFeature(featureName) {

    featureSteps.forEach((step) => {

        if (step.dataset.feature === featureName) {

            step.classList.add("active");

        } else {

            step.classList.remove("active");

        }

    });


    previewPanels.forEach((panel) => {

        if (panel.dataset.preview === featureName) {

            panel.classList.add("active");

        } else {

            panel.classList.remove("active");

        }

    });


    progressDots.forEach((dot) => {

        if (dot.dataset.target === featureName) {

            dot.classList.add("active");

        } else {

            dot.classList.remove("active");

        }

    });

}



/*
    Watch each feature section.

    When one enters the central part
    of the screen, make that feature active.
*/

const observerOptions = {

    root: null,

    rootMargin:
        "-35% 0px -35% 0px",

    threshold: 0

};


const featureObserver =
    new IntersectionObserver(
        (entries) => {

            entries.forEach((entry) => {

                if (entry.isIntersecting) {

                    const featureName =
                        entry.target.dataset.feature;

                    activateFeature(featureName);

                }

            });

        },
        observerOptions
    );


featureSteps.forEach((step) => {

    featureObserver.observe(step);

});



/*
    Allow the progress buttons beneath
    the preview to jump to a feature.
*/

progressDots.forEach((dot) => {

    dot.addEventListener(
        "click",
        () => {

            const targetName =
                dot.dataset.target;

            const matchingStep =
                document.querySelector(
                    `[data-feature="${targetName}"]`
                );

            if (matchingStep) {

                matchingStep.scrollIntoView({

                    behavior: "smooth",

                    block: "center"

                });

            }

        }
    );

});


async function refreshNotificationCount() {

    const response = await fetch(
        "/notifications/count",
        {
            cache: "no-store"
        }
    );

    const data = await response.json();

    const badge = document.querySelector(
        ".notification-badge"
    );


    if (badge) {

        if (data.count > 0) {

            badge.textContent = data.count;

            badge.style.display = "inline-flex";

        } else {

            badge.style.display = "none";

        }

    }

}


window.addEventListener(
    "pageshow",
    refreshNotificationCount
);



async function refreshMessageCounts() {

    try {

        const response = await fetch(
            "/messages/unread",
            {
                cache: "no-store"
            }
        );

        const data = await response.json();


        // Individual conversation cards
        document.querySelectorAll(
            ".messages-card"
        ).forEach((card) => {

            const conversationId =
                card.dataset.conversationId;

            const unreadCount =
                Number(
                    data.conversations[
                        conversationId
                    ] || 0
                );

            const badge =
                card.querySelector(
                    ".messages-unread-badge"
                );


            card.classList.toggle(
                "messages-card-unread",
                unreadCount > 0
            );


            if (badge) {

                badge.textContent =
                    unreadCount;

                badge.style.display =
                    unreadCount > 0
                        ? "inline-flex"
                        : "none";

            }

        });

    } catch (error) {

        console.error(
            "Could not refresh message counts:",
            error
        );

    }

}


window.addEventListener(
    "pageshow",
    refreshMessageCounts
);

if (
    document.body.classList.contains(
        "notifications-page"
    )
) {

    let notificationsPageAlreadyShown = false;

    window.addEventListener(
        "pageshow",
        () => {

            if (notificationsPageAlreadyShown) {

                document.querySelectorAll(
                    ".notification-unread"
                ).forEach((notification) => {

                    notification.classList.remove(
                        "notification-unread"
                    );

                });

            }

            notificationsPageAlreadyShown = true;

        }
    );

}

function scrollConversationToBottom() {

    const messageForm =
        document.querySelector(
            "#message-form"
        );

    if (messageForm) {

        messageForm.scrollIntoView({
            block: "end"
        });

    }

}


window.addEventListener(
    "pageshow",
    scrollConversationToBottom
);

const messageForm =
    document.querySelector(
        "#message-form"
    );


if (messageForm) {

    messageForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();


            const formData =
                new FormData(messageForm);


            const content =
                String(
                    formData.get("content") || ""
                ).trim();


            if (!content) {
                return;
            }


            /*
                Remember exactly where the
                message form currently appears
                on the screen.
            */

            const formPositionBefore =
                messageForm
                    .getBoundingClientRect()
                    .top;


            const submitButton =
                messageForm.querySelector(
                    'button[type="submit"]'
                );


            if (submitButton) {
                submitButton.disabled = true;
            }


            try {

                const response =
                    await fetch(
                        messageForm.action,
                        {
                            method: "POST",
                            body: formData
                        }
                    );


                if (!response.ok) {

                    throw new Error(
                        "Could not send message."
                    );

                }


                /*
                    Flask redirects to the updated
                    conversation after saving the
                    message.

                    fetch follows that redirect in
                    the background without moving
                    the browser away from this page.
                */

                const html =
                    await response.text();


                const parser =
                    new DOMParser();


                const updatedPage =
                    parser.parseFromString(
                        html,
                        "text/html"
                    );


                const updatedMessages =
                    updatedPage.querySelector(
                        ".conversation-messages"
                    );


                const currentMessages =
                    document.querySelector(
                        ".conversation-messages"
                    );


                if (
                    updatedMessages &&
                    currentMessages
                ) {

                    currentMessages.innerHTML =
                        updatedMessages.innerHTML;

                }


                messageForm.reset();


                /*
                    A new message has been added
                    above the form.

                    Keep the form at exactly the
                    same visual position.
                */

                const formPositionAfter =
                    messageForm
                        .getBoundingClientRect()
                        .top;


                const scrollDifference =
                    formPositionAfter -
                    formPositionBefore;


                const previousScrollBehavior =
                    document.documentElement.style.scrollBehavior;


                document.documentElement.style.scrollBehavior =
                    "auto";


                window.scrollBy(
                    0,
                    scrollDifference
                );


document.documentElement.style.scrollBehavior =
    previousScrollBehavior;


            } catch (error) {

                console.error(
                    "Could not send message:",
                    error
                );

            } finally {

                if (submitButton) {
                    submitButton.disabled = false;
                }

            }

        }
    );

}