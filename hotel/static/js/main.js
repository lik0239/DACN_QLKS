document.addEventListener("DOMContentLoaded", function () {
    const toggleBtn = document.querySelector("#userIcon");
    const dropdownMenu = document.getElementById("userDropdown");
    const toggleWrapper = document.querySelector(".user-toggle");

    if (toggleBtn && dropdownMenu) {
        toggleBtn.addEventListener("click", function (event) {
            event.stopPropagation();

            const isOpen = dropdownMenu.style.display === "block";

            dropdownMenu.style.display = isOpen ? "none" : "block";
            toggleWrapper.classList.toggle("open", !isOpen);  // 👉 Thêm class 'open' nếu dropdown mở
        });
    }

    // Đóng dropdown nếu click ra ngoài
    window.addEventListener("click", function (e) {
        const toggle = document.querySelector(".user-toggle");
        if (toggle && !toggle.contains(e.target)) {
            dropdownMenu.style.display = "none";
            toggle.classList.remove("open"); // 👉 Gỡ class 'open' khi đóng
        }
    });
});
