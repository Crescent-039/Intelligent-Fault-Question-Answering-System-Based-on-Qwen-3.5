#ifndef CONFIG_H
#define CONFIG_H

#include <QString>

class config
{
public:
    inline static const QString ip = "ws://127.0.0.1:11451/ws";
    inline static const int retryDelayms = 1000;
};

#endif // CONFIG_H
