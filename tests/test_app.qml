import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 640
    height: 480
    title: "qt-pilot test app"

    property string currentPage: "main"

    function navigateTo(page) {
        currentPage = page
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12

        Text {
            text: "Test Application"
            font.pixelSize: 24
        }

        Text {
            text: "Page: " + window.currentPage
            font.pixelSize: 14
        }

        TextField {
            id: usernameField
            placeholderText: "Username"
            Layout.fillWidth: true
        }

        TextField {
            id: passwordField
            placeholderText: "Password"
            echoMode: TextInput.Password
            Layout.fillWidth: true
        }

        Button {
            id: loginButton
            text: "Sign In"
            Layout.fillWidth: true
        }

        Button {
            id: otherButton
            text: "Other Action"
            Layout.fillWidth: true
            enabled: false
        }

        CheckBox {
            id: rememberMe
            text: "Remember me"
        }

        Item { Layout.fillHeight: true }
    }
}
