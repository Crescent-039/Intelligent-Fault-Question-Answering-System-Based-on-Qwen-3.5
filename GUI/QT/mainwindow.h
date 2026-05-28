#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QThread>
#include <QLabel>
#include <QResizeEvent>
#include <QPushButton>

#include <webSocket/socketclient.h>
#include <config.h>

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

protected:
    void resizeEvent(QResizeEvent *event) override;

private:
    void showOverlay(const QString &text);
    void initLayout();
    void showConnectingOverlay(const QString &text);
    void hideConnectingOverlay();

public:
    QString address;
private:
    Ui::MainWindow *ui;
    SocketClient *wsClient;
    QWidget *overlay = nullptr;
    QLabel *overlayLabel = nullptr;

private slots:
    void onSendCLLL();
};
#endif // MAINWINDOW_H
