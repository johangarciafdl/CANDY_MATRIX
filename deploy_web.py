# deploy_web.py
"""Compila la versión web y la publica en GitHub Pages en un solo paso.

    .venv\\Scripts\\python deploy_web.py

Queda en https://johangarciafdl.github.io/CANDY_MATRIX/ un minuto después.

La rama `gh-pages` guarda solo el resultado de compilar (index.html, web.apk,
favicon.png), no el código. Por eso un commit en `master` no cambia el sitio:
hay que recompilar y volver a subir, que es lo que hace este script.

Trabaja en un `git worktree` temporal en vez de cambiar de rama: así tu carpeta
del proyecto nunca cambia de rama ni pierde cambios sin commitear, aunque el
script falle a la mitad.
"""
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(RAIZ, "web", "build", "web")
ARCHIVOS = ("index.html", "web.apk", "web.tar.gz", "favicon.png", "sw.js", "Fredoka-700.ttf")
URL = "https://johangarciafdl.github.io/CANDY_MATRIX/"


def git(*args, cwd=RAIZ, capturar=False):
    resultado = subprocess.run(["git", *args], cwd=cwd, text=True,
                               capture_output=capturar)
    if resultado.returncode != 0:
        if capturar:
            sys.stderr.write(resultado.stderr)
        sys.exit("git %s falló" % " ".join(args))
    return resultado.stdout.strip() if capturar else None


def main():
    # 1. Compilar (incluye las verificaciones de build_web.py)
    codigo = subprocess.call([sys.executable, os.path.join(RAIZ, "build_web.py")], cwd=RAIZ)
    if codigo != 0:
        sys.exit("La compilación falló; no se publica nada.")

    commit = git("rev-parse", "--short", "HEAD", capturar=True)
    sucio = git("status", "--porcelain", capturar=True)

    # 2. Copiar el resultado a gh-pages en un worktree aparte
    wt = tempfile.mkdtemp(prefix="candy-deploy-")
    shutil.rmtree(wt)  # git worktree add quiere crear la carpeta él mismo
    git("worktree", "add", "--quiet", wt, "gh-pages")
    try:
        for nombre in ARCHIVOS:
            shutil.copy2(os.path.join(SALIDA, nombre), os.path.join(wt, nombre))

        git("add", "-A", cwd=wt)
        if not git("status", "--porcelain", cwd=wt, capturar=True):
            print("\nEl sitio ya tiene esta versión; no hay nada que publicar.")
            return 0

        mensaje = "Publicar build de %s%s" % (commit, " (con cambios sin commitear)" if sucio else "")
        git("commit", "--quiet", "-m", mensaje, cwd=wt)
        git("push", "--quiet", "origin", "gh-pages", cwd=wt)
    finally:
        git("worktree", "remove", "--force", wt)

    print("\nPublicado: %s" % URL)
    print("GitHub tarda alrededor de un minuto en servirlo. Si ves la versión")
    print("anterior, recarga forzando (Ctrl+F5) o borra los datos del sitio en el celular.")
    if sucio:
        print("\nOjo: había cambios sin commitear, así que lo publicado no coincide")
        print("con ningún commit de master.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
