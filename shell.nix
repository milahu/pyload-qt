{
  pkgs ? import <nixpkgs> { }
}:

pkgs.mkShell {
  buildInputs = with pkgs; [
    (python3.withPackages (pp: with pp; [
      pyside6
      black
    ]))
  ];
  # fix: qt.qpa.plugin: From 6.5.0, xcb-cursor0 or libxcb-cursor0 is needed to load the Qt xcb platform plugin.
  # https://github.com/NixOS/nixpkgs/issues/431908
  shellHook = ''
    export QT_PLUGIN_PATH=${with pkgs.libsForQt5; "${qtbase}/${qtbase.qtPluginPrefix}"}
  '';
}
