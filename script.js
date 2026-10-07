/* =====================================================
   AURELIA ESTATES — JAVASCRIPT
   ===================================================== */

document.addEventListener("DOMContentLoaded", () => {

    /* ================= FAVORITE BUTTONS ================= */

    document.addEventListener("click", (event) => {
        const button = event.target.closest(".favorite-btn");
        if (!button) return;

        button.classList.toggle("active");
        button.textContent = button.classList.contains("active") ? "♥" : "♡";
    });

    loadProperties();


    /* ================= SEARCH BUTTON ================= */

    const searchButton = document.querySelector(".search-btn");

    if (searchButton) {

        searchButton.addEventListener("click", () => {

            const propertiesSection =
                document.querySelector("#properties");

            if (propertiesSection) {

                propertiesSection.scrollIntoView({
                    behavior: "smooth"
                });

            }

        });

    }


    /* ================= NAVBAR SCROLL EFFECT ================= */

    const navbar = document.querySelector(".navbar");

    window.addEventListener("scroll", () => {

        if (window.scrollY > 80) {

            navbar.style.background = "rgba(8, 8, 8, 0.94)";
            navbar.style.padding = "15px 0";

        } else {

            navbar.style.background = "rgba(8, 8, 8, 0.72)";
            navbar.style.padding = "22px 0";

        }

    });


    /* ================= SCROLL REVEAL ================= */

    const revealElements = document.querySelectorAll(
        ".property-card, .about-image, .about-content, .service-card, .cta-content"
    );

    const revealObserver = new IntersectionObserver(
        (entries, observer) => {

            entries.forEach((entry) => {

                if (entry.isIntersecting) {

                    entry.target.classList.add("show");

                    observer.unobserve(entry.target);

                }

            });

        },
        {
            threshold: 0.12
        }
    );


    revealElements.forEach((element) => {

        element.classList.add("reveal");

        revealObserver.observe(element);

    });


    /* ================= ACTIVE NAVIGATION ================= */

    const navLinks = document.querySelectorAll(".nav-menu a");

    navLinks.forEach((link) => {

        link.addEventListener("click", () => {

            navLinks.forEach((item) => {
                item.classList.remove("current");
            });

            link.classList.add("current");

        });

    });


    /* ================= CONTACT BUTTON ================= */

    const contactButtons = document.querySelectorAll(
        'a[href="#contact"]'
    );

    contactButtons.forEach((button) => {

        button.addEventListener("click", () => {

            const contactSection =
                document.querySelector("#contact");

            if (contactSection) {

                contactSection.scrollIntoView({
                    behavior: "smooth"
                });

            }

        });

    });


    /* ================= PAGE LOADED ================= */

    document.body.classList.add("page-loaded");

});
async function loadProperties() {
    const propertyGrid = document.getElementById("propertyGrid");
    if (!propertyGrid) return;

    try {
        const response = await fetch("/api/properties");
        if (!response.ok) throw new Error("Properties could not be loaded.");

        const { properties } = await response.json();
        propertyGrid.replaceChildren();

        properties.forEach((property) => {
            const imageUrl = new URL(property.image_url);
            if (imageUrl.protocol !== "https:") return;

            const card = document.createElement("article");
            card.className = "property-card reveal";

            const image = document.createElement("div");
            image.className = "property-image";
            image.style.backgroundImage = `linear-gradient(to top, rgba(0,0,0,0.75), transparent 55%), url("${imageUrl.href}")`;

            const status = document.createElement("span");
            status.className = "property-status";
            status.textContent = property.status;

            const favorite = document.createElement("button");
            favorite.className = "favorite-btn";
            favorite.type = "button";
            favorite.setAttribute("aria-label", `Save ${property.title} to favorites`);
            favorite.textContent = "♡";

            const price = document.createElement("div");
            price.className = "property-price";
            price.textContent = `$${Number(property.price).toLocaleString("en-US")}`;
            image.append(status, favorite, price);

            const info = document.createElement("div");
            info.className = "property-info";

            const location = document.createElement("p");
            location.className = "property-location";
            location.textContent = `📍 ${property.location}`;

            const title = document.createElement("h3");
            title.textContent = property.title;

            const details = document.createElement("div");
            details.className = "property-details";
            [`${property.beds} Beds`, `${property.baths} Baths`, `${Number(property.area_sqft).toLocaleString("en-US")} sq ft`]
                .forEach((detail) => {
                    const item = document.createElement("span");
                    item.textContent = detail;
                    details.append(item);
                });

            info.append(location, title, details);
            card.append(image, info);
            propertyGrid.append(card);
            requestAnimationFrame(() => card.classList.add("show"));
        });

        if (!propertyGrid.childElementCount) {
            propertyGrid.textContent = "No properties are available right now.";
        }
    } catch (error) {
        propertyGrid.textContent = "Properties are temporarily unavailable.";
    }
}

const contactForm = document.getElementById("contactForm");
const formMessage = document.getElementById("formMessage");

if (contactForm) {
    contactForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        formMessage.textContent = "Sending your inquiry...";

        const submitButton = contactForm.querySelector('[type="submit"]');
        submitButton.disabled = true;

        const payload = Object.fromEntries(new FormData(contactForm).entries());

        try {
            const response = await fetch("/api/inquiries", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "Your inquiry could not be sent.");

            formMessage.textContent =
                `Thank you, ${result.name}. Your inquiry has been received. Our property specialist will contact you shortly.`;
            contactForm.reset();
        } catch (error) {
            formMessage.textContent = error.message || "Unable to send your inquiry. Please try again.";
        } finally {
            submitButton.disabled = false;
        }
    });
}
