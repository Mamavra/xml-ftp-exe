Tento balík je pripravený na vytvorenie Windows 10 EXE cez GitHub Actions.

Obsah:
- xml_decimal_ftp.py
- config.json
- .github/workflows/build-exe.yml

Postup:
1. Vytvor si nový repozitár na GitHube.
2. Nahraj tam celý obsah tohto balíka.
3. Otvor GitHub -> Actions.
4. Spusť workflow "Build Windows EXE".
5. Po dokončení stiahni artifact "xml_decimal_ftp_windows".
6. V ňom bude xml_decimal_ftp.exe.

Poznámka:
EXE je buildované na Windows runneri, takže bude vhodné pre Windows 10.
Config.json musí byť pri EXE v rovnakom priečinku.
