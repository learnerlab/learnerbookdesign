/**
 * Book Cover Swiper - Tinder-style card swiping engine.
 */
(function () {
    let covers = [];
    let currentIndex = 0;
    let totalSwiped = 0;
    let startX = 0, startY = 0, currentX = 0, isDragging = false;

    const stack = document.getElementById("card-stack");
    const counterEl = document.getElementById("counter");

    async function loadCovers() {
        try {
            const resp = await fetch("/api/covers?limit=30");
            const data = await resp.json();
            covers = data;
            currentIndex = 0;
            renderCards();
        } catch (err) {
            stack.innerHTML = `<div class="empty-state"><h2>Connection Error</h2><p>Could not load covers. Is the server running?</p></div>`;
        }
    }

    function renderCards() {
        stack.innerHTML = "";
        if (currentIndex >= covers.length) {
            if (covers.length > 0) {
                // Load more
                loadCovers();
            } else {
                stack.innerHTML = `
                    <div class="empty-state">
                        <h2>No more covers!</h2>
                        <p>You've swiped through all available covers.<br>Covers are being scraped from ineedabookcover.com — check back soon!</p>
                        <button onclick="location.reload()" class="btn" style="margin-top:1rem;">Refresh</button>
                    </div>`;
            }
            return;
        }

        // Show up to 3 stacked cards
        const visibleCount = Math.min(3, covers.length - currentIndex);
        for (let i = visibleCount - 1; i >= 0; i--) {
            const cover = covers[currentIndex + i];
            const card = createCard(cover, i);
            stack.appendChild(card);
        }

        // Make the top card draggable
        const topCard = stack.lastElementChild;
        if (topCard) {
            attachDragListeners(topCard);
        }
        updateCounter();
    }

    function createCard(cover, stackIndex) {
        const card = document.createElement("div");
        card.className = "card";
        card.dataset.coverId = cover.id;

        // Stack offset effect
        const scale = 1 - stackIndex * 0.04;
        const translateY = stackIndex * 8;
        card.style.transform = `translateY(${translateY}px) scale(${scale})`;
        card.style.zIndex = 10 - stackIndex;

        const genre = cover.genre || "";
        const genreHtml = genre ? `<span class="genre">${escapeHtml(genre)}</span>` : "";
        const authorHtml = cover.author ? `<div class="author">${escapeHtml(cover.author)}</div>` : "";
        const sourceHtml = cover.source ? `<div class="source">${escapeHtml(cover.source)}</div>` : "";

        card.innerHTML = `
            <div class="swipe-indicator like">LIKE</div>
            <div class="swipe-indicator dislike">NOPE</div>
            <img class="card-image" src="${escapeHtml(cover.image_url)}" alt="${escapeHtml(cover.title)}"
                 onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22320%22 height=%22380%22><rect fill=%22%23222%22 width=%22320%22 height=%22380%22/><text x=%2250%25%22 y=%2250%25%22 fill=%22%23555%22 text-anchor=%22middle%22 dominant-baseline=%22middle%22 font-family=%22sans-serif%22 font-size=%2216%22>Cover not available</text></svg>'">
            <div class="card-info">
                <h3>${escapeHtml(cover.title)}</h3>
                ${authorHtml}
                ${genreHtml}
                ${sourceHtml}
            </div>
        `;
        return card;
    }

    function attachDragListeners(card) {
        // Touch events
        card.addEventListener("touchstart", onDragStart, { passive: true });
        card.addEventListener("touchmove", onDragMove, { passive: false });
        card.addEventListener("touchend", onDragEnd);

        // Mouse events
        card.addEventListener("mousedown", onDragStart);
    }

    function onDragStart(e) {
        isDragging = true;
        const point = e.touches ? e.touches[0] : e;
        startX = point.clientX;
        startY = point.clientY;
        currentX = 0;

        if (!e.touches) {
            document.addEventListener("mousemove", onDragMove);
            document.addEventListener("mouseup", onDragEnd);
        }
    }

    function onDragMove(e) {
        if (!isDragging) return;
        if (e.cancelable) e.preventDefault();

        const point = e.touches ? e.touches[0] : e;
        currentX = point.clientX - startX;
        const currentY = point.clientY - startY;

        const topCard = stack.lastElementChild;
        if (!topCard || !topCard.classList.contains("card")) return;

        const rotation = currentX * 0.08;
        topCard.style.transform = `translateX(${currentX}px) translateY(${currentY * 0.3}px) rotate(${rotation}deg)`;

        // Show like/dislike indicator
        const likeIndicator = topCard.querySelector(".swipe-indicator.like");
        const dislikeIndicator = topCard.querySelector(".swipe-indicator.dislike");

        const threshold = 60;
        if (currentX > threshold) {
            likeIndicator.style.opacity = Math.min((currentX - threshold) / 80, 1);
            dislikeIndicator.style.opacity = 0;
        } else if (currentX < -threshold) {
            dislikeIndicator.style.opacity = Math.min((-currentX - threshold) / 80, 1);
            likeIndicator.style.opacity = 0;
        } else {
            likeIndicator.style.opacity = 0;
            dislikeIndicator.style.opacity = 0;
        }
    }

    function onDragEnd() {
        if (!isDragging) return;
        isDragging = false;

        document.removeEventListener("mousemove", onDragMove);
        document.removeEventListener("mouseup", onDragEnd);

        const swipeThreshold = 100;
        if (currentX > swipeThreshold) {
            performSwipe("like");
        } else if (currentX < -swipeThreshold) {
            performSwipe("dislike");
        } else {
            // Snap back
            const topCard = stack.lastElementChild;
            if (topCard) {
                topCard.style.transition = "transform 0.3s ease";
                topCard.style.transform = "translateX(0) translateY(0) rotate(0)";
                setTimeout(() => { topCard.style.transition = ""; }, 300);

                const likeInd = topCard.querySelector(".swipe-indicator.like");
                const dislikeInd = topCard.querySelector(".swipe-indicator.dislike");
                if (likeInd) likeInd.style.opacity = 0;
                if (dislikeInd) dislikeInd.style.opacity = 0;
            }
        }
    }

    function performSwipe(action) {
        const topCard = stack.lastElementChild;
        if (!topCard || !topCard.classList.contains("card")) return;

        const coverId = parseInt(topCard.dataset.coverId);

        // Animate out
        topCard.classList.add("removing", action === "like" ? "liked" : action === "dislike" ? "disliked" : "superliked");

        // Record swipe
        fetch("/api/swipe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cover_id: coverId, action: action }),
        });

        totalSwiped++;

        setTimeout(() => {
            currentIndex++;
            renderCards();
        }, 400);
    }

    function updateCounter() {
        const remaining = covers.length - currentIndex;
        counterEl.textContent = `${remaining} covers remaining | ${totalSwiped} swiped this session`;
    }

    function escapeHtml(str) {
        if (!str) return "";
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    // --- Keyboard shortcuts ---
    document.addEventListener("keydown", (e) => {
        if (e.key === "ArrowLeft" || e.key === "a") {
            performSwipe("dislike");
        } else if (e.key === "ArrowRight" || e.key === "d") {
            performSwipe("like");
        } else if (e.key === "ArrowUp" || e.key === "w") {
            performSwipe("superlike");
        }
    });

    // --- Button clicks ---
    document.getElementById("btn-dislike")?.addEventListener("click", () => performSwipe("dislike"));
    document.getElementById("btn-like")?.addEventListener("click", () => performSwipe("like"));
    document.getElementById("btn-superlike")?.addEventListener("click", () => performSwipe("superlike"));

    // --- Init ---
    loadCovers();
})();
