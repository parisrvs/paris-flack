document.addEventListener('DOMContentLoaded', () => {
    document.querySelector("#login_form").onsubmit = ()=> {
        let username = document.querySelector("#username").value;
        let password = document.querySelector("#password").value;
        if (username.length <= 0) {
            alert("Type a Username");
            return false;
        }
        if (password.length <= 0) {
            alert("Type a Password");
            return false;
        }
    };
});