{
  pkgs ? import <nixpkgs> { }
}:

pkgs.mkShell {
  buildInputs = with pkgs; [
    (python3.withPackages (pp: with pp; [
      pyside6
      black
      # pyqt only
      # https://github.com/lxqt/qtermwidget/issues/536#issuecomment-2227574817
      # nur.repos.milahu.python3.pkgs.qtermwidget
      nur.repos.milahu.python3.pkgs.qtpyterminal
    ]))
  ];
}
