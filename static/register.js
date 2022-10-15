document.addEventListener('DOMContentLoaded', () => {
    document.querySelector("#register_form").onsubmit = ()=> {
        let username = document.querySelector("#username").value;
        let password = document.querySelector("#password").value;
        let password1 = document.querySelector("#password1").value;
        let email = document.querySelector("#email").value;

        if (username.length < 4) {
            alert("Type a Username - Minimum 4 Characters Long");
            return false;
        }
        if (email.length <= 0) {
            alert("Type your Email");
            return false;
        }
        if (password.length < 6) {
            alert("Type a Password - Minimum 6 Characters Long");
            return false;
        }
        if (password1 != password) {
            alert("Passwords Don't Match");
            return false;
        }
        
    };
});