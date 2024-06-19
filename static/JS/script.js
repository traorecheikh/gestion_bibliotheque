document
  .getElementById("togglePassword")
  .addEventListener("click", function () {
    var passwordInput = document.getElementById("mot_de_passe");
    if (passwordInput.type === "password") {
      passwordInput.type = "text";
      this.textContent = "Masquer";
    } else {
      passwordInput.type = "password";
      this.textContent = "Afficher";
    }
  });
