import QtQuick
import Quickshell

// The Chromarchy artwork behind the lock screen's password field: PNGs rendered
// by src/build.py for a 1920x1080 screen, scaled to whatever this screen is.
//
// The password box image is drawn here; LockView puts the real TextInput on top
// of fieldX/fieldY/fieldW/fieldH.
Item {
  id: scene

  property int variant: 1
  property bool running: true

  readonly property real k: Math.min(width / 1920, height / 1080)
  readonly property var v: specs[variant] || specs[1]

  readonly property real fieldW: entry.implicitWidth * k
  readonly property real fieldH: entry.implicitHeight * k
  readonly property real fieldX: Math.round((width - fieldW) / 2)
  readonly property real fieldY: Math.round(stage.y + logo.implicitHeight * k + 40 * k)

  // Per-variant styling that isn't baked into the PNGs. bulletDx/footerGap
  // mirror meta.json; the rest styles the live text input.
  readonly property var specs: ({
    1: { bg: "#1a1b26", ink: "#dfe3f0", hintColor: "#565f89", font: "JetBrainsMono Nerd Font", radius: 6,
         bulletDx: 20, footerGap: 40, dot: "●",
         hint: "Password", fail: "Wrong password" },
    2: { bg: "#202124", ink: "#e8eaed", hintColor: "#9aa0a6", font: "Liberation Sans", radius: 24,
         bulletDx: 52, footerGap: 34, dot: "●",
         hint: "Search the Arch Wiki or type your password", fail: "Did you mean: your actual password?" },
    3: { bg: "#202124", ink: "#acacac", hintColor: "#9aa0a6", font: "JetBrainsMono Nerd Font", radius: 2,
         bulletDx: 20, footerGap: 40, dot: "■",
         hint: "Password (works offline)", fail: "ERR_WRONG_PASSWORD" },
    4: { bg: "#0c0c10", ink: "#f5f5f5", hintColor: "#8a8a96", font: "Adwaita Sans", radius: 0,
         bulletDx: 20, footerGap: 40, dot: "●",
         hint: "Password", fail: "Off the track. Try again" },
    5: { bg: "#202124", ink: "#e8eaed", hintColor: "#9aa0a6", font: "Adwaita Sans", radius: 23,
         bulletDx: 52, footerGap: 44, dot: "●",
         hint: "Type your password or a URL", fail: "This password can’t be reached" }
  })

  function asset(name) { return Qt.resolvedUrl("assets/v" + scene.variant + "-" + name + ".png") }

  Rectangle {
    anchors.fill: parent
    color: scene.v.bg
  }

  // Full-width browser chrome pinned to the top (chrome://omarchy)
  Image {
    id: topBar
    visible: scene.variant === 5
    source: scene.variant === 5 ? scene.asset("top") : ""
    width: parent.width
    height: implicitWidth > 0 ? implicitHeight * width / implicitWidth : 0

    // Profile avatar initial, from whoever is logged in. The circle sits at
    // (1844, 66) in the 1920-wide artwork.
    Text {
      readonly property real s: topBar.width / 1920
      text: (Quickshell.env("USER") || "?").charAt(0).toUpperCase()
      color: "#ffffff"
      font.family: "Adwaita Sans"
      font.weight: Font.Bold
      font.pixelSize: Math.round(15 * s)
      x: 1844 * s - width / 2
      y: 66 * s - height / 2
    }
  }

  // Logo (and the dino game) at design pixels, scaled as one unit
  Item {
    id: stage
    width: logo.implicitWidth
    height: logo.implicitHeight
    x: Math.round((scene.width - width * scene.k) / 2)
    y: Math.round((scene.height - height * scene.k) / 2)
    scale: scene.k
    transformOrigin: Item.TopLeft

    Image { id: logo; source: scene.asset("logo") }

    Loader {
      active: scene.variant === 3
      sourceComponent: dinoGame
    }
  }

  Image {
    id: entry
    source: scene.asset("entry")
    x: scene.fieldX
    y: scene.fieldY
    width: scene.fieldW
    height: scene.fieldH
  }

  // Padlock left of the box, 80% of its height (blank 84x96 for the search-box variants)
  Image {
    source: scene.asset("lock")
    height: scene.fieldH * 0.8
    width: height * 84 / 96
    x: scene.fieldX - width - 15 * scene.k
    y: scene.fieldY + (scene.fieldH - height) / 2
  }

  Image {
    id: footer
    visible: scene.variant === 2 || scene.variant === 5
    source: visible && (scene.variant === 2 || scene.variant === 5) ? scene.asset("footer") : ""
    width: implicitWidth * scene.k
    height: implicitHeight * scene.k
    x: Math.round((scene.width - width) / 2)
    y: scene.fieldY + scene.fieldH + scene.v.footerGap * scene.k
  }

  // ---------------------------------------------------------------- dino game
  // Same rules as src/simulate.py, which checks that the dino always clears
  // the cacti. Coordinates are scene pixels.
  Component {
    id: dinoGame

    Item {
      id: game

      // Fixed to the dino's own assets so a variant switch never points these at another design's files
      function asset(name) { return Qt.resolvedUrl("assets/v3-" + name + ".png") }

      readonly property var cfg: ({ sceneW: 820, groundY: 180, dinoX: 90, dinoW: 80, dinoH: 80,
                                  speed: 6, scoreX: 685, scoreY: 8, digitW: 13 })
      property real h: 0
      property real vy: 0
      property bool air: false
      property int leg: 0
      property int legT: 0
      property var cx: [620, 1050, 1480]
      property var big: [true, false, true]
      property var clouds: [430, 660]
      property real peb: 0
      property int score: 0
      property int scoreT: 0

      function tick() {
        var x = cx.slice(), b = big.slice()
        for (var i = 0; i < 3; i++) {
          x[i] -= cfg.speed
          if (x[i] < -100) {
            x[i] = Math.max(cfg.sceneW, x[0], x[1], x[2]) + 340 + Math.floor(Math.random() * 320)
            b[i] = Math.random() < 0.5
          }
        }
        cx = x; big = b

        // vy 10, gravity 0.5: 40 frames airborne, clearing 60px for ~25 frames
        if (!air) {
          for (var j = 0; j < 3; j++) {
            var gap = cx[j] - (cfg.dinoX + cfg.dinoW)
            if (gap > 0 && gap <= 54) { air = true; vy = 10 }
          }
        }
        if (air) {
          h += vy
          vy -= 0.5
          if (h <= 0) { h = 0; air = false }
        } else if (++legT >= 5) {
          legT = 0
          leg = 1 - leg
        }

        var c = clouds.slice()
        for (var n = 0; n < 2; n++) {
          c[n] -= 0.5
          if (c[n] < -80) c[n] = cfg.sceneW + 40 + Math.floor(Math.random() * 200)
        }
        clouds = c

        peb -= cfg.speed
        if (peb <= -cfg.sceneW) peb += cfg.sceneW

        if (++scoreT >= 5) {
          scoreT = 0
          score = (score + 1) % 100000
        }
      }

      Timer {
        interval: 20
        repeat: true
        running: scene.running
        onTriggered: game.tick()
      }

      Image { source: game.asset("pebbles"); x: game.peb; y: game.cfg.groundY + 2 }

      Repeater {
        model: 2
        Image { source: game.asset("cloud"); x: game.clouds[index]; y: 50 + index * 26 }
      }

      Repeater {
        model: 3
        Image {
          source: game.asset(game.big[index] ? "cactus-big" : "cactus-small")
          x: game.cx[index]
          y: game.cfg.groundY - (game.big[index] ? 60 : 44) + 2
        }
      }

      Repeater {
        model: ["dino-run1", "dino-run2", "dino-jump"]
        Image {
          source: game.asset(modelData)
          visible: game.air ? index === 2 : index === game.leg
          x: game.cfg.dinoX
          y: game.cfg.groundY - game.cfg.dinoH + 4 - game.h
        }
      }

      Repeater {
        model: 5
        Image {
          source: game.asset("digit-" + String(game.score).padStart(5, "0")[index])
          x: game.cfg.scoreX + index * game.cfg.digitW
          y: game.cfg.scoreY
        }
      }

      // Background-colored masks fade the scene edges and hide what scrolls past them
      Image { source: game.asset("mask-left"); x: -900; y: 0 }
      Image { source: game.asset("mask-right"); x: game.cfg.sceneW - 60; y: 0 }
    }
  }
}
