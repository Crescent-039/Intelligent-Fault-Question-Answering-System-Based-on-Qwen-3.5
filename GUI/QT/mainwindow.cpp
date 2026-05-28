#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QVBoxLayout>
#include <QSizePolicy>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    wsClient = new SocketClient(this);
    connect(wsClient, &SocketClient::messageReceived, this, [=](const QString &msg){
            ui->msgDisplay->appendPlainText(msg);
        });
    connect(ui->sendCLLL, &QPushButton::clicked, this, &MainWindow::onSendCLLL);
    initLayout();
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::initLayout()
{
    overlay = new QWidget(centralWidget());
    overlay->setGeometry(centralWidget()->rect());
    overlay->setStyleSheet("background-color: rgba(0, 0, 0, 160);");

    overlayLabel = new QLabel("连接中，请等待...", overlay);
    overlayLabel->setStyleSheet(
        "color: white;"
        "font-size: 28px;"
        "font-weight: bold;"
        "background-color: transparent;"
    );
    overlayLabel->setAlignment(Qt::AlignCenter);
    overlayLabel->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);

    QVBoxLayout *layout = new QVBoxLayout(overlay);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);
    layout->addWidget(overlayLabel);

    overlay->show();
    overlay->raise();

    connect(wsClient, &SocketClient::connected, this, [=]() {
        qDebug() << "主界面：连接成功";
        hideConnectingOverlay();
    });
    connect(wsClient, &SocketClient::disconnected, this, [=]() {
        qDebug() << "主界面：连接断开";
        showConnectingOverlay("连接已断开，正在重连...");
    });
    connect(wsClient, &SocketClient::errorOccurred, this, [=](const QString &msg) {
        qDebug() << "主界面：连接错误" << msg;
        showConnectingOverlay("连接服务器失败，正在重试...");
    });
}

void MainWindow::resizeEvent(QResizeEvent *event)
{
    QMainWindow::resizeEvent(event);

    if (overlay && centralWidget()) {
        overlay->setGeometry(centralWidget()->rect());
        overlay->raise();
    }
}


void MainWindow::showOverlay(const QString &text)
{
    if (!overlay || !overlayLabel) {
        return;
    }

    overlayLabel->setText(text);
    overlay->setGeometry(centralWidget()->rect());
    overlay->show();
    overlay->raise();
}

void MainWindow::showConnectingOverlay(const QString &text)
{
    if (!overlay || !overlayLabel) {
        return;
    }

    overlayLabel->setText(text);
    overlay->setGeometry(centralWidget()->rect());
    overlay->show();
    overlay->raise();
}
void MainWindow::hideConnectingOverlay()
{
    if (overlay) {
        overlay->hide();
    }
}

void MainWindow::onSendCLLL()
{
    wsClient->sendMsg("草里来来");
}













































