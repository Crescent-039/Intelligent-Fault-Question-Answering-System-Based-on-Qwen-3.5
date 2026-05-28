#ifndef SOCKETCLIENT_H
#define SOCKETCLIENT_H

#include <QObject>
#include <QWebSocket>
#include <QTimer>

#include <config.h>

class SocketClient : public QObject
{
    Q_OBJECT
public:
    explicit SocketClient(QObject *parent = nullptr);
    QAbstractSocket::SocketState state() const;
    void tryReconnect();
    void sendMsg(QString message);


signals:
    void messageReceived(const QString &message);
    // 转发状态给前端
    void connected();
    void disconnected();
    void errorOccurred(const QString &msg);

private slots:
    void onConnected();
    void onTextMessageReceived(const QString &message);

private:
    QWebSocket m_webSocket;
    QString m_url;
    QTimer m_reconnectTimer;

};

#endif // SOCKETCLIENT_H
