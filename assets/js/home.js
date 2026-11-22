const SERVICES_CONFIG = "/services.json";

const ICONS = {
    "book-open": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 7v14"/><path d="M3 18V5a2 2 0 0 1 2-2h3a4 4 0 0 1 4 4 4 4 0 0 1 4-4h3a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2h-3a4 4 0 0 0-4 2 4 4 0 0 0-4-2H5a2 2 0 0 1-2-2Z"/></svg>`,
    "layers": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 16 9 5 9-5"/></svg>`,
    "graduation-cap": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="m2 10 10-5 10 5-10 5-10-5Z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/><path d="M22 10v6"/></svg>`,
    "brain": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 18V5"/><path d="M15.5 4a3.5 3.5 0 0 1 5 3 3 3 0 0 1-1 2.3 3.5 3.5 0 0 1-1 6.7A3.5 3.5 0 0 1 15 20"/><path d="M8.5 4a3.5 3.5 0 0 0-5 3 3 3 0 0 0 1 2.3 3.5 3.5 0 0 0 1 6.7A3.5 3.5 0 0 0 9 20"/></svg>`
};

function createServiceCard(service) {
    const card = document.createElement("a");
    card.className = "service-card";
    card.href = service.url || "#";
    card.dataset.serviceId = service.id || "";

    const icon = document.createElement("span");
    icon.className = "service-icon";
    icon.innerHTML = ICONS[service.icon] || ICONS["book-open"];

    const content = document.createElement("span");
    content.className = "service-content";

    const title = document.createElement("span");
    title.className = "service-title";
    title.textContent = service.title || "سرویس بدون عنوان";

    const description = document.createElement("span");
    description.className = "service-description";
    description.textContent = service.description || "";

    const arrow = document.createElement("span");
    arrow.className = "service-arrow";
    arrow.textContent = "←";

    content.append(title, description);
    card.append(icon, content, arrow);

    return card;
}

async function loadServices() {
    const container = document.getElementById("services-container");
    if (!container) return;

    try {
        const response = await fetch(
            `${SERVICES_CONFIG}?v=${Date.now()}`
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const services = await response.json();

        if (!Array.isArray(services)) {
            throw new Error("Invalid services configuration");
        }

        const activeServices = services
            .filter(service => service.status === "active")
            .sort((a, b) => (a.order || 999) - (b.order || 999));

        container.replaceChildren();

        activeServices.forEach(service => {
            container.appendChild(createServiceCard(service));
        });

        if (activeServices.length === 0) {
            container.textContent = "در حال حاضر سرویسی برای نمایش وجود ندارد.";
        }

    } catch (error) {
        console.error("Medisource services error:", error);
        container.textContent = "بارگذاری سرویس‌ها با مشکل مواجه شد.";
    }
}

document.addEventListener("DOMContentLoaded", loadServices);

/* ============ MEDISOURCE CONTACT INTERACTIONS ============ */

document.addEventListener("DOMContentLoaded", () => {

    // Scroll reveal
    const revealItems = document.querySelectorAll(".contact-reveal");

    if (!("IntersectionObserver" in window)) {
        revealItems.forEach(item => item.classList.add("visible"));
    } else {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("visible");
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.15,
            rootMargin: "0px 0px -40px 0px"
        });

        revealItems.forEach(item => observer.observe(item));
    }

    // Mouse-following glow
    document.querySelectorAll(".contact-card").forEach(card => {
        card.addEventListener("pointermove", event => {
            const rect = card.getBoundingClientRect();

            const x = ((event.clientX - rect.left) / rect.width) * 100;
            const y = ((event.clientY - rect.top) / rect.height) * 100;

            card.style.setProperty("--mx", `${x}%`);
            card.style.setProperty("--my", `${y}%`);
        });
    });

    // Footer year, if present
    const yearElement = document.getElementById("year");

    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }
});
