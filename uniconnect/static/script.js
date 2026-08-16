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