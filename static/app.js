"use strict";

let cameraStream = null;
let currentFacingMode = "environment";
let selectedImageFile = null;
let selectedImageUrl = null;

function syncViewportHeight() {
    const height = window.visualViewport
        ? window.visualViewport.height
        : window.innerHeight;
    document.documentElement.style.setProperty("--visual-height", `${height}px`);
}

syncViewportHeight();
window.addEventListener("resize", syncViewportHeight, { passive: true });
if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", syncViewportHeight, { passive: true });
}


document.addEventListener("DOMContentLoaded", function () {

    document.querySelectorAll(".post-action[data-like-post]").forEach(function (button) {
        const postId = button.dataset.likePost;
        const liked = localStorage.getItem(`relife-liked-${postId}`) === "1";
        button.classList.toggle("liked", liked);
        button.setAttribute("aria-pressed", liked ? "true" : "false");
        button.setAttribute("aria-label", liked ? "إلغاء الإعجاب" : "إعجاب");
    });

    document.querySelectorAll(".post-photo-wrap .community-photo").forEach(function (photo) {
        const wrapper = photo.closest(".post-photo-wrap");
        if (wrapper) wrapper.style.setProperty("--post-bg", `url("${photo.currentSrc || photo.src}")`);
    });

    const onboardingScreen = document.getElementById("onboardingScreen");
    const startAppButton = document.getElementById("startAppButton");
    let onboardingSeen = false;

    try {
        onboardingSeen = localStorage.getItem("relife-onboarding-seen") === "1";
    } catch (error) {
        onboardingSeen = false;
    }

    if (onboardingScreen) {
        if (onboardingSeen) {
            onboardingScreen.remove();
        } else {
            document.body.classList.add("onboarding-open");
        }
    }

    if (startAppButton && onboardingScreen) {
        startAppButton.addEventListener("click", function () {
            try {
                localStorage.setItem("relife-onboarding-seen", "1");
            } catch (error) {
                // Private browsing may block storage; closing still works.
            }
            onboardingScreen.classList.add("is-leaving");
            document.body.classList.remove("onboarding-open");
            window.setTimeout(function () {
                onboardingScreen.remove();
                const cameraButton = document.getElementById("openCameraButton");
                if (cameraButton) cameraButton.focus({ preventScroll: true });
            }, 420);
        });
    }

    const bottomNavigation = document.querySelector(".bottom-navigation");
    if (bottomNavigation) {
        const cameraNav = bottomNavigation.querySelector(".nav-camera");
        if (cameraNav && !cameraNav.querySelector("span")) {
            const label = document.createElement("span");
            label.textContent = "التصوير";
            cameraNav.appendChild(label);
        }

        if (!bottomNavigation.querySelector('[href="/impact"]')) {
            const impactLink = document.createElement("a");
            impactLink.href = "/impact";
            impactLink.className = "nav-link";
            impactLink.innerHTML = '<svg viewBox="0 0 24 24"><path d="m12 3 2.5 5.1 5.6.8-4 3.9.9 5.5-5-2.7-5 2.7.9-5.5-4-3.9 5.6-.8L12 3Z"/></svg><span>أثري</span>';
            const communityLink = bottomNavigation.querySelector('a[href*="community"]');
            bottomNavigation.insertBefore(impactLink, communityLink || null);
        }
    }
    if (bottomNavigation && bottomNavigation.parentElement !== document.body) {
        document.body.appendChild(bottomNavigation);
    }

    requestAnimationFrame(function () {
        document.body.classList.add("page-ready");
    });

    const openCameraButton =
        document.getElementById("openCameraButton");

    const bottomCameraButton =
        document.getElementById("bottomCameraButton");

    const closeCameraButton =
        document.getElementById("closeCameraButton");

    const captureButton =
        document.getElementById("captureButton");

    const switchCameraButton =
        document.getElementById("switchCameraButton");

    const galleryInput =
        document.getElementById("galleryInput");

    const cameraGalleryButton =
        document.getElementById("cameraGalleryButton");

    const removePhotoButton =
        document.getElementById("removePhotoButton");

    const analyzeForm = document.getElementById("analyzeForm");
    if (analyzeForm) {
        analyzeForm.addEventListener("submit", function () {
            const button = document.getElementById("analyzeButton");
            const loading = document.getElementById("analysisLoading");
            const loadingText = document.getElementById("analysisLoadingText");
            if (button) {
                button.disabled = true;
                button.textContent = "جاري التحليل وتوليد الاقتراحات…";
            }
            if (loading) {
                loading.classList.remove("hidden");
                document.body.style.overflow = "hidden";
            }

            const stages = [
                "نحلل العنصر والمواد…",
                "نبتكر أربع أفكار سهلة ومفيدة…",
                "نرسم شكل الاقتراحات من صورتك…",
                "نجهّز خطوات التنفيذ…"
            ];
            let stage = 0;
            window.setInterval(function () {
                stage = Math.min(stage + 1, stages.length - 1);
                if (loadingText) loadingText.textContent = stages[stage];
            }, 4500);
        });
    }


    /* =========================================
       CAMERA BUTTON
    ========================================= */

    if (openCameraButton) {
        openCameraButton.addEventListener(
            "click",
            openCamera
        );
    }


    if (bottomCameraButton) {
        bottomCameraButton.addEventListener(
            "click",
            openCamera
        );
    }


    if (closeCameraButton) {
        closeCameraButton.addEventListener(
            "click",
            closeCamera
        );
    }


    if (captureButton) {
        captureButton.addEventListener(
            "click",
            capturePhoto
        );
    }


    if (switchCameraButton) {
        switchCameraButton.addEventListener(
            "click",
            switchCamera
        );
    }


    /* =========================================
       GALLERY
    ========================================= */

    if (galleryInput) {

        galleryInput.addEventListener(
            "change",
            function () {

                const file =
                    this.files &&
                    this.files.length > 0
                        ? this.files[0]
                        : null;


                if (!file) {
                    return;
                }


                closeCamera();


                showSelectedImage(
                    file
                );
            }
        );
    }


    /* =========================================
       GALLERY FROM CAMERA
    ========================================= */

    if (cameraGalleryButton) {

        cameraGalleryButton.addEventListener(
            "click",
            function () {

                stopCameraStream();


                const cameraScreen =
                    document.getElementById(
                        "cameraScreen"
                    );


                if (cameraScreen) {
                    cameraScreen.classList.add(
                        "hidden"
                    );
                }


                document.body.style.overflow = "";
            }
        );
    }


    /* =========================================
       REMOVE PHOTO
    ========================================= */

    if (removePhotoButton) {

        removePhotoButton.addEventListener(
            "click",
            clearSelectedImage
        );
    }


    /* =========================================
       MODAL
    ========================================= */

    const postModal =
        document.getElementById("postModal");


    if (postModal) {

        postModal.addEventListener(
            "click",
            function (event) {

                if (event.target === postModal) {
                    closePostModal();
                }
            }
        );
    }

    const postImageInput = document.getElementById("postImageInput");
    const removePostImage = document.getElementById("removePostImage");
    let postPreviewUrl = null;

    if (postImageInput) {
        postImageInput.addEventListener("change", function () {
            const file = this.files && this.files[0];
            const wrap = document.getElementById("postImagePreview");
            const preview = document.getElementById("postPreviewImage");
            if (!file || !wrap || !preview) return;
            if (postPreviewUrl) URL.revokeObjectURL(postPreviewUrl);
            postPreviewUrl = URL.createObjectURL(file);
            preview.src = postPreviewUrl;
            wrap.classList.remove("hidden");
        });
    }

    if (removePostImage) {
        removePostImage.addEventListener("click", function () {
            const wrap = document.getElementById("postImagePreview");
            const preview = document.getElementById("postPreviewImage");
            if (postImageInput) postImageInput.value = "";
            if (postPreviewUrl) URL.revokeObjectURL(postPreviewUrl);
            postPreviewUrl = null;
            if (preview) preview.src = "";
            if (wrap) wrap.classList.add("hidden");
        });
    }


    /* =========================================
       OPEN CAMERA FROM OTHER PAGE
       /#camera
    ========================================= */

    if (
        window.location.hash === "#camera"
    ) {

        history.replaceState(
            null,
            "",
            window.location.pathname
        );


        setTimeout(
            function () {
                openCamera();
            },
            250
        );
    }

});


/* =========================================================
   OPEN CAMERA
========================================================= */

async function openCamera() {

    const cameraScreen =
        document.getElementById(
            "cameraScreen"
        );


    const cameraVideo =
        document.getElementById(
            "cameraVideo"
        );


    const cameraMessage =
        document.getElementById(
            "cameraMessage"
        );


    if (
        !cameraScreen ||
        !cameraVideo
    ) {

        console.error(
            "Camera HTML elements not found"
        );

        return;
    }


    cameraScreen.classList.remove(
        "hidden"
    );


    document.body.style.overflow =
        "hidden";


    if (cameraMessage) {

        cameraMessage.classList.add(
            "hidden"
        );

        cameraMessage.textContent = "";
    }


    if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia
    ) {

        showCameraError(
            window.isSecureContext
                ? "المتصفح لا يدعم فتح الكاميرا مباشرة. استخدم الاستديو."
                : "فتح الكاميرا يحتاج اتصال HTTPS أو localhost. يمكنك استخدام الاستديو الآن."
        );

        return;
    }


    stopCameraStream();


    try {

        cameraStream =
            await navigator.mediaDevices
                .getUserMedia({

                    audio: false,

                    video: {

                        facingMode: {
                            ideal:
                                currentFacingMode
                        },

                        width: {
                            ideal: 1920
                        },

                        height: {
                            ideal: 1080
                        }
                    }
                });


        cameraVideo.srcObject =
            cameraStream;


        await cameraVideo.play();


        updateCameraSwitchAvailability();

    }

    catch (error) {

        console.error(
            "Camera error:",
            error
        );


        if (
            error.name ===
            "NotAllowedError"
        ) {

            showCameraError(
                "تم رفض إذن الكاميرا. اسمح للموقع باستخدام الكاميرا من إعدادات المتصفح."
            );

        }

        else if (
            error.name ===
            "NotFoundError"
        ) {

            showCameraError(
                "لم يتم العثور على كاميرا."
            );

        }

        else if (
            error.name ===
            "NotReadableError"
        ) {

            showCameraError(
                "الكاميرا مستخدمة بواسطة تطبيق آخر."
            );

        }

        else {

            showCameraError(
                "تعذر تشغيل الكاميرا. يمكنك اختيار صورة من الاستديو."
            );
        }
    }
}


/* =========================================================
   CAMERA ERROR
========================================================= */

function showCameraError(message) {

    const element =
        document.getElementById(
            "cameraMessage"
        );


    if (!element) {
        return;
    }


    element.textContent =
        message;


    element.classList.remove(
        "hidden"
    );
}


/* =========================================================
   STOP CAMERA
========================================================= */

function stopCameraStream() {

    if (!cameraStream) {
        return;
    }


    cameraStream
        .getTracks()
        .forEach(
            function (track) {
                track.stop();
            }
        );


    cameraStream = null;


    const video =
        document.getElementById(
            "cameraVideo"
        );


    if (video) {
        video.srcObject = null;
    }
}


async function updateCameraSwitchAvailability() {
    const button = document.getElementById("switchCameraButton");
    if (!button || !navigator.mediaDevices.enumerateDevices) return;

    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const cameras = devices.filter(function (device) {
            return device.kind === "videoinput";
        });
        button.hidden = cameras.length < 2;
    } catch (error) {
        button.hidden = false;
    }
}


/* =========================================================
   CLOSE CAMERA
========================================================= */

function closeCamera() {

    stopCameraStream();


    const screen =
        document.getElementById(
            "cameraScreen"
        );


    if (screen) {

        screen.classList.add(
            "hidden"
        );
    }


    document.body.style.overflow = "";
}


/* =========================================================
   SWITCH CAMERA
========================================================= */

async function switchCamera() {

    currentFacingMode =
        currentFacingMode === "environment"
            ? "user"
            : "environment";


    stopCameraStream();


    await openCamera();
}


/* =========================================================
   CAPTURE
========================================================= */

function capturePhoto() {

    const video =
        document.getElementById(
            "cameraVideo"
        );


    const canvas =
        document.getElementById(
            "cameraCanvas"
        );


    if (
        !video ||
        !canvas ||
        !video.videoWidth ||
        !video.videoHeight
    ) {

        showCameraError(
            "انتظر حتى تعمل الكاميرا."
        );

        return;
    }


    canvas.width =
        video.videoWidth;


    canvas.height =
        video.videoHeight;


    const context =
        canvas.getContext(
            "2d"
        );


    context.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );


    canvas.toBlob(

        function (blob) {

            if (!blob) {
                return;
            }


            const file =
                new File(

                    [blob],

                    "camera-photo.jpg",

                    {
                        type:
                            "image/jpeg"
                    }
                );


            putCameraFileIntoInput(
                file
            );

            const cameraImageData = document.getElementById("cameraImageData");
            if (cameraImageData) {
                cameraImageData.value = canvas.toDataURL("image/jpeg", 0.9);
            }


            showSelectedImage(
                file
            );


            closeCamera();

        },

        "image/jpeg",

        0.9
    );
}


/* =========================================================
   CAMERA FILE -> INPUT
========================================================= */

function putCameraFileIntoInput(file) {

    selectedImageFile = file;

    const input =
        document.getElementById(
            "galleryInput"
        );


    if (!input) {
        return;
    }


    try {

        const transfer =
            new DataTransfer();


        transfer.items.add(
            file
        );


        input.files =
            transfer.files;

    }

    catch (error) {
        // Safari versions that do not allow assigning input.files use
        // the hidden camera_image field populated by capturePhoto().
    }
}


/* =========================================================
   SHOW PREVIEW
========================================================= */

function showSelectedImage(file) {

    const preview =
        document.getElementById(
            "selectedImage"
        );


    const card =
        document.getElementById(
            "selectedImageCard"
        );


    if (
        !preview ||
        !card
    ) {

        console.error(
            "Preview HTML elements not found"
        );

        return;
    }


    if (selectedImageUrl) {
        URL.revokeObjectURL(selectedImageUrl);
    }

    selectedImageFile = file;
    selectedImageUrl =
        URL.createObjectURL(
            file
        );


    preview.src =
        selectedImageUrl;


    card.classList.remove(
        "hidden"
    );

    const scanPanel = document.querySelector(".scan-panel");
    if (scanPanel) scanPanel.classList.add("has-image");


    setTimeout(
        function () {

            card.scrollIntoView({

                behavior:
                    "smooth",

                block:
                    "nearest"
            });

        },

        100
    );
}


/* =========================================================
   CLEAR IMAGE
========================================================= */

function clearSelectedImage() {

    const input =
        document.getElementById(
            "galleryInput"
        );


    const preview =
        document.getElementById(
            "selectedImage"
        );


    const card =
        document.getElementById(
            "selectedImageCard"
        );


    if (input) {
        input.value = "";
    }

    const cameraImageData = document.getElementById("cameraImageData");
    if (cameraImageData) cameraImageData.value = "";

    selectedImageFile = null;

    if (selectedImageUrl) {
        URL.revokeObjectURL(selectedImageUrl);
        selectedImageUrl = null;
    }


    if (preview) {
        preview.src = "";
    }


    if (card) {

        card.classList.add(
            "hidden"
        );
    }

    const scanPanel = document.querySelector(".scan-panel");
    if (scanPanel) scanPanel.classList.remove("has-image");
}


window.addEventListener("pagehide", function () {
    stopCameraStream();
    if (selectedImageUrl) URL.revokeObjectURL(selectedImageUrl);
});

if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", function () {
        navigator.serviceWorker.register("/static/sw.js").catch(function () {
            // The app remains fully functional when service workers are unavailable.
        });
    });
}


/* =========================================================
   COMMUNITY MODAL
========================================================= */

function openPostModal() {

    const modal =
        document.getElementById(
            "postModal"
        );


    if (!modal) {
        return;
    }


    modal.classList.remove(
        "hidden"
    );


    document.body.style.overflow =
        "hidden";

    const firstField = modal.querySelector("input, textarea");
    if (firstField) window.setTimeout(function () { firstField.focus(); }, 120);
}


function closePostModal() {

    const modal =
        document.getElementById(
            "postModal"
        );


    if (!modal) {
        return;
    }


    modal.classList.add(
        "hidden"
    );


    document.body.style.overflow = "";
}


/* =========================================================
   LIKE
========================================================= */

async function likePost(
    postId,
    button
) {

    const storageKey = `relife-liked-${postId}`;
    if (button.dataset.pending === "true") return;

    const wasLiked = localStorage.getItem(storageKey) === "1";
    const nextLiked = !wasLiked;
    let likerId = localStorage.getItem("relife-liker-id");
    if (!likerId) {
        likerId = window.crypto && window.crypto.randomUUID
            ? window.crypto.randomUUID()
            : `device-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        localStorage.setItem("relife-liker-id", likerId);
    }

    button.dataset.pending = "true";
    button.disabled = true;

    try {

        const response =
            await fetch(
                `/community/like/${postId}`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        liked: nextLiked,
                        liker_id: likerId
                    })
                }
            );


        const result =
            await response.json();


        if (!result.success) {
            return;
        }


        const number =
            button.querySelector(
                "span"
            );


        if (number) {

            number.textContent =
                result.likes;
        }


        button.classList.toggle("liked", result.liked);
        button.setAttribute("aria-pressed", result.liked ? "true" : "false");
        button.setAttribute("aria-label", result.liked ? "إلغاء الإعجاب" : "إعجاب");

        if (result.liked) {
            localStorage.setItem(storageKey, "1");
            showToast("وصل إعجابك لصاحب الفكرة 💚");
        } else {
            localStorage.removeItem(storageKey);
            showToast("تم إلغاء الإعجاب");
        }

    }

    catch (error) {

        console.error(
            "Like error:",
            error
        );
        showToast("تعذر تسجيل الإعجاب، حاول مرة أخرى");
    } finally {
        button.dataset.pending = "false";
        button.disabled = false;
    }
}


async function sharePost(caption) {
    const shareData = {
        title: "مجتمع إعادة الاستخدام",
        text: caption,
        url: window.location.href
    };

    try {
        if (navigator.share) {
            await navigator.share(shareData);
        } else if (navigator.clipboard) {
            await navigator.clipboard.writeText(`${caption}\n${window.location.href}`);
            showToast("تم نسخ رابط المشاركة");
        }
    } catch (error) {
        if (error.name !== "AbortError") console.error("Share error:", error);
    }
}


function showToast(message) {
    let toast = document.getElementById("appToast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "appToast";
        toast.className = "app-toast";
        toast.setAttribute("role", "status");
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(function () {
        toast.classList.remove("show");
    }, 2600);
}


/* =========================================================
   ESCAPE
========================================================= */

document.addEventListener(
    "keydown",
    function (event) {

        if (
            event.key === "Escape"
        ) {

            closeCamera();

            closePostModal();
        }
    }
);


/* =========================================================
   CLEANUP
========================================================= */
