#include "socketclient.h"

SocketClient::SocketClient(QObject *parent) : QObject(parent)
{
    m_url = config::ip;
    m_reconnectTimer.setInterval(config::retryDelayms);
    m_reconnectTimer.setSingleShot(true);
    m_reconnectTimer.start();
    connect(&m_reconnectTimer, &QTimer::timeout,
            this, &SocketClient::tryReconnect);

    connect(&m_webSocket, &QWebSocket::textMessageReceived, this, &SocketClient::onTextMessageReceived);

    connect(&m_webSocket, &QWebSocket::connected, this, [this]() {
        emit connected();
        m_reconnectTimer.stop();
    });
    connect(&m_webSocket, &QWebSocket::disconnected, this, [this]() {
        emit disconnected();
        if (!m_reconnectTimer.isActive())
            m_reconnectTimer.start();
    });
    connect(&m_webSocket,
            QOverload<QAbstractSocket::SocketError>::of(&QWebSocket::error),
            this,
            [this](QAbstractSocket::SocketError error) {
                Q_UNUSED(error);
                emit errorOccurred(m_webSocket.errorString());
                if (!m_reconnectTimer.isActive())
                    m_reconnectTimer.start();
            });
}

void SocketClient::onConnected()
{
    qDebug() << "已成功连接到 Python 后端";
    m_webSocket.sendTextMessage("Hello Python, 我是 Qt!");
}

void SocketClient::onTextMessageReceived(const QString &message)
{
    qDebug() << "收到后端传来的消息:" << message;
    emit messageReceived(message);
}

QAbstractSocket::SocketState SocketClient::state() const
{
    return m_webSocket.state();
}

void SocketClient::tryReconnect()
{
    if (m_webSocket.state() == QAbstractSocket::ConnectedState ||
        m_webSocket.state() == QAbstractSocket::ConnectingState) {
        return;
    }
    qDebug() << "尝试重新连接:" << m_url;
    m_webSocket.open(QUrl(m_url));
}

void SocketClient::sendMsg(QString message)
{
    m_webSocket.sendTextMessage(message);
}
