// =========================
// CHECK EXISTING SESSION
// =========================

(async function checkExistingSession() {

    try {

        const response = await fetch(
            "/api/me",
            {
                method: "GET",
                credentials: "same-origin",
                cache: "no-store"
            }
        );

        if (response.ok) {

            window.location.replace("/");

        }

    } catch (error) {

        console.log(
            "No active session."
        );

    }

})();


// =========================
// CONSTELLATION
// =========================

function buildConstellation() {

    const wrap =
        document.getElementById(
            "constellation"
        );

    if (!wrap) return;


    const points = [

        {
            id: "node-1",
            x: 12,
            y: 15,
            label: "quarterly-report.pdf"
        },

        {
            id: "node-2",
            x: 62,
            y: 37,
            label: "→ answer"
        },

        {
            id: "node-3",
            x: 18,
            y: 60,
            label: "research-notes.pdf"
        },

        {
            id: "node-4",
            x: 56,
            y: 77,
            label: "→ answer"
        },

        {
            id: "node-5",
            x: 80,
            y: 22,
            label: "contract.pdf"
        }

    ];


    points.forEach(
        (point, index) => {

            const el =
                document.createElement(
                    "div"
                );

            el.className =
                `node node-${index + 1}`;

            el.style.top =
                `${point.y}%`;

            el.style.left =
                `${point.x}%`;

            el.innerHTML =
                `<span>${point.label}</span>`;

            wrap.appendChild(el);

        }
    );

}

buildConstellation();


// =========================
// LOGIN / SIGNUP TABS
// =========================

const tabLogin =
    document.getElementById(
        "tabLogin"
    );

const tabSignup =
    document.getElementById(
        "tabSignup"
    );

const togglePill =
    document.getElementById(
        "togglePill"
    );

const loginForm =
    document.getElementById(
        "loginForm"
    );

const signupForm =
    document.getElementById(
        "signupForm"
    );


function activateTab(
    target
) {

    const showSignup =
        target === "signup";


    tabLogin.classList.toggle(
        "active",
        !showSignup
    );

    tabSignup.classList.toggle(
        "active",
        showSignup
    );

    togglePill.classList.toggle(
        "shift",
        showSignup
    );

    loginForm.classList.toggle(
        "active",
        !showSignup
    );

    signupForm.classList.toggle(
        "active",
        showSignup
    );

}


tabLogin.addEventListener(
    "click",
    () =>
        activateTab("login")
);


tabSignup.addEventListener(
    "click",
    () =>
        activateTab("signup")
);


// =========================
// PASSWORD VISIBILITY
// =========================

document
    .querySelectorAll(
        ".toggle-visibility"
    )
    .forEach(
        (btn) => {

            btn.addEventListener(
                "click",
                () => {

                    const targetId =
                        btn.getAttribute(
                            "data-target"
                        );

                    const input =
                        document.getElementById(
                            targetId
                        );

                    const isPassword =
                        input.type ===
                        "password";

                    input.type =
                        isPassword
                            ? "text"
                            : "password";

                    btn.style.color =
                        isPassword
                            ? "var(--accent)"
                            : "var(--text-muted)";

                }
            );

        }
    );


// =========================
// HELPERS
// =========================

function showError(
    element,
    message
) {

    element.textContent =
        message;

    element.classList.add(
        "visible"
    );

}


function hideError(
    element
) {

    element.classList.remove(
        "visible"
    );

}


function setLoading(
    button,
    loading
) {

    button.classList.toggle(
        "loading",
        loading
    );

    button.disabled =
        loading;

}


// =========================
// AUTH REQUEST
// =========================

async function submitAuth(
    url,
    payload,
    submitBtn,
    errorEl
) {

    hideError(
        errorEl
    );

    setLoading(
        submitBtn,
        true
    );


    try {

        const response =
            await fetch(
                url,
                {

                    method: "POST",

                    credentials:
                        "same-origin",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify(
                            payload
                        )

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Something went wrong."
            );

        }


        // IMPORTANT:
        // Verify that the session cookie
        // actually works before redirecting.

        const sessionResponse =
            await fetch(
                "/api/me",
                {

                    method: "GET",

                    credentials:
                        "same-origin",

                    cache:
                        "no-store"

                }
            );


        if (!sessionResponse.ok) {

            throw new Error(
                "Login succeeded, but the session was not created. Please try again."
            );

        }


        submitBtn
            .querySelector(
                ".btn-label"
            )
            .textContent =
                "Success!";


        window.location.replace(
            "/"
        );

    }

    catch (error) {

        console.error(
            "Authentication error:",
            error
        );

        showError(
            errorEl,
            error.message
        );

        setLoading(
            submitBtn,
            false
        );

    }

}


// =========================
// LOGIN
// =========================

loginForm.addEventListener(
    "submit",
    (event) => {

        event.preventDefault();


        const email =
            document
                .getElementById(
                    "loginEmail"
                )
                .value
                .trim();


        const password =
            document
                .getElementById(
                    "loginPassword"
                )
                .value;


        const errorEl =
            document.getElementById(
                "loginError"
            );


        if (
            !email ||
            !password
        ) {

            showError(
                errorEl,
                "Please fill in both fields."
            );

            return;

        }


        submitAuth(

            "/api/login",

            {
                email:
                    email,

                password:
                    password
            },

            document.getElementById(
                "loginSubmit"
            ),

            errorEl

        );

    }
);


// =========================
// SIGN UP
// =========================

signupForm.addEventListener(
    "submit",
    (event) => {

        event.preventDefault();


        const name =
            document
                .getElementById(
                    "signupName"
                )
                .value
                .trim();


        const email =
            document
                .getElementById(
                    "signupEmail"
                )
                .value
                .trim();


        const password =
            document
                .getElementById(
                    "signupPassword"
                )
                .value;


        const errorEl =
            document.getElementById(
                "signupError"
            );


        if (
            !name ||
            !email ||
            !password
        ) {

            showError(
                errorEl,
                "Please fill in all fields."
            );

            return;

        }


        if (
            password.length < 6
        ) {

            showError(
                errorEl,
                "Password must be at least 6 characters long."
            );

            return;

        }


        submitAuth(

            "/api/signup",

            {
                name:
                    name,

                email:
                    email,

                password:
                    password
            },

            document.getElementById(
                "signupSubmit"
            ),

            errorEl

        );

    }
);