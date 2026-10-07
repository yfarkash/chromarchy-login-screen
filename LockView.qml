import QtQuick
import qs.Commons
import qs.Ui

// Chromarchy lock view: Omarchy's LockView (LockView.upstream.qml) with the
// blurred wallpaper replaced by a ChromarchyScene picked at random on each lock.
// The password handling (TextInput, signals, focus, failure states) is upstream's,
// only restyled and repositioned onto the scene's password box.
Item {
  id: root

  property string backgroundPath: ""
  property int backgroundVersion: 0
  property bool fingerprintConfigured: false
  property bool authenticatingPassword: false
  property string failureMessage: ""
  property int failedAttempts: 0
  property bool inputEnabled: true
  property bool loadBackground: true
  property string passwordText: ""
  property bool syncingPasswordText: false

  // Variants to rotate between. The real lock picks one at random; the preview
  // (omarchy-shell lock preview) steps through them in order.
  readonly property var rotation: [1, 2, 3, 4, 5]
  property int variant: rotation[0]
  property int previewIndex: 0

  readonly property var spec: scene.v
  readonly property real k: scene.k
  readonly property int fieldFontSize: Math.max(10, Math.round(16 * k))
  readonly property int passwordDotFontSize: Math.max(10, Math.round(15 * k))
  readonly property int passwordDotLetterSpacing: Math.round(4 * k)
  readonly property real fingerprintReserve: fingerprintConfigured ? Math.round(fingerprintIcon.implicitWidth + 12) : 0
  // Shrink the dots to fit once the password outgrows the field, so every
  // keystroke stays visible — otherwise long passwords clip with no feedback.
  readonly property real passwordDotScale: dotMetrics.advanceWidth > 0
    ? Math.min(1, (passwordInput.width - 4) / dotMetrics.advanceWidth)
    : 1
  readonly property bool showPasswordCursor: inputEnabled && !authenticatingPassword && failureMessage.length === 0
  readonly property bool errorState: failureMessage.length > 0
  // Only the generic PAM failure gets the variant's joke; lockout and other
  // messages are shown as Omarchy wrote them.
  readonly property string shownFailure: failureMessage.indexOf("Authentication failed") === 0
    ? spec.fail + " (" + failedAttempts + ")"
    : failureMessage

  signal submitPassword(string password)
  signal passwordTextEdited(string password)
  signal clearFailureRequested()
  signal wakeRequested()

  function pickVariant() {
    if (inputEnabled) {
      variant = rotation[Math.floor(Math.random() * rotation.length)]
    } else {
      variant = rotation[previewIndex % rotation.length]
      previewIndex += 1
    }
  }

  function forcePasswordFocus() {
    passwordInput.forceActiveFocus()
  }

  function clearPassword() {
    passwordTextEdited("")
  }

  function syncPasswordText() {
    if (passwordInput.text === passwordText) return
    syncingPasswordText = true
    passwordInput.text = passwordText
    syncingPasswordText = false
  }

  onPasswordTextChanged: syncPasswordText()
  onLoadBackgroundChanged: if (loadBackground) pickVariant()
  onInputEnabledChanged: {
    if (inputEnabled) Qt.callLater(forcePasswordFocus)
  }
  Component.onCompleted: {
    pickVariant()
    syncPasswordText()
    if (inputEnabled) Qt.callLater(forcePasswordFocus)
  }

  // Measures the masked password at full size; passwordDotScale compares this
  // against the field width to decide how far the dots must shrink to fit.
  TextMetrics {
    id: dotMetrics
    font.family: Style.font.family
    font.pixelSize: root.passwordDotFontSize
    font.letterSpacing: root.passwordDotLetterSpacing
    text: root.spec.dot.repeat(passwordInput.text.length)
  }

  ChromarchyScene {
    id: scene
    anchors.fill: parent
    variant: root.variant
    running: root.loadBackground
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    onClicked: { root.wakeRequested(); root.forcePasswordFocus() }
    onPositionChanged: root.wakeRequested()
  }

  Item {
    id: inputField
    x: scene.fieldX
    y: scene.fieldY
    width: scene.fieldW
    height: scene.fieldH
    clip: true

    TextInput {
      id: passwordInput
      anchors.fill: parent
      anchors.leftMargin: root.spec.bulletDx * root.k
      anchors.rightMargin: 14 * root.k + root.fingerprintReserve
      verticalAlignment: TextInput.AlignVCenter
      horizontalAlignment: TextInput.AlignLeft
      activeFocusOnPress: true
      clip: true
      enabled: root.inputEnabled && !root.authenticatingPassword
      readOnly: root.authenticatingPassword
      echoMode: TextInput.Password
      passwordCharacter: root.spec.dot
      passwordMaskDelay: 0
      color: root.spec.ink
      selectionColor: Color.lock.selection
      selectedTextColor: root.spec.ink
      font.family: Style.font.family
      font.pixelSize: text.length > 0 ? Math.max(1, Math.floor(root.passwordDotFontSize * root.passwordDotScale)) : root.fieldFontSize
      font.letterSpacing: text.length > 0 ? root.passwordDotLetterSpacing * root.passwordDotScale : 0
      cursorVisible: activeFocus && root.showPasswordCursor && text.length > 0
      cursorDelegate: Rectangle {
        width: 2
        color: root.spec.ink
        visible: passwordInput.cursorVisible
      }

      onTextChanged: {
        if (!root.syncingPasswordText) root.passwordTextEdited(text)
        if (text.length > 0) {
          root.wakeRequested()
        }
        if (text.length > 0 && root.failureMessage.length > 0) root.clearFailureRequested()
      }

      onAccepted: {
        var submitted = root.passwordText
        root.passwordTextEdited("")
        if (submitted.length > 0) root.submitPassword(submitted)
      }

      Keys.onPressed: function(event) {
        root.wakeRequested()
        if (event.key === Qt.Key_Escape || (event.modifiers & Qt.ControlModifier && event.key === Qt.Key_U)) {
          root.passwordTextEdited("")
          event.accepted = true
        }
      }
    }

    Text {
      textFormat: Text.PlainText
      anchors.fill: passwordInput
      text: root.authenticatingPassword ? "Checking…" : (root.errorState ? root.shownFailure : root.spec.hint)
      visible: passwordInput.text.length === 0
      color: root.authenticatingPassword ? root.spec.ink : (root.errorState ? Color.lock.textError : root.spec.hintColor)
      font.family: root.spec.font
      font.pixelSize: root.fieldFontSize
      font.italic: !root.authenticatingPassword && root.errorState
      horizontalAlignment: Text.AlignLeft
      verticalAlignment: Text.AlignVCenter
      elide: Text.ElideRight
    }

    // Fingerprint hint pinned inside the field's right edge when a sensor is
    // enrolled, so the user knows they can touch to unlock instead of typing.
    Text {
      id: fingerprintIcon
      objectName: "fingerprintIndicator"
      anchors.right: parent.right
      anchors.rightMargin: 14 * root.k
      anchors.verticalCenter: parent.verticalCenter
      visible: root.fingerprintConfigured
      text: "󰈷"
      color: root.spec.hintColor
      font.family: Style.font.family
      font.pixelSize: Math.round(root.fieldFontSize * 1.1)
      horizontalAlignment: Text.AlignHCenter
      verticalAlignment: Text.AlignVCenter
    }
  }

  // Error outline over the box image, matching each variant's corner radius
  Rectangle {
    x: inputField.x
    y: inputField.y
    width: inputField.width
    height: inputField.height
    radius: root.spec.radius * root.k
    color: "transparent"
    border.width: Math.max(2, Math.round(2 * root.k))
    border.color: Color.lock.borderError
    visible: root.errorState
  }
}
