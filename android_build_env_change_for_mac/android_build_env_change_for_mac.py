# coding=gbk

# Android4.X在OS X10.10.X上编译时，由于Android源码的配置原因无法直接正确的编译，
# 需要修改一些配置才能正确的编译，这个脚本就是用于自动化修改Android源码的配置，修改完成后
# 可以使Android4.X在OS X10.10.X上正确编译。

# 需要说明的是：Android4.X编译所使用的jdk必须是jdk6，所以如果你的电脑上没有jdk6，那么请下载。

'''

脚本参数说明：
-d：可选参数，指定Android源码根目录。如果本脚本在Android源码根目录，那么可以不输入这个参数，否则必须输入这个参数。
-j：可选参数，jdk6的java home路径。如果你的电脑上的jdk环境变量是jdk6，那么可以不输入这个选项，
    否则要么输入这个参数，要么你自己设置jdk6的环境变量。注意：本脚本设置的环境变量只在当前终端上下文中有效。
'''

__author__ = 'buwai'

import os
import sys
import getopt
import commands
import shutil
import logging
import re

class MacAndroidBuildEnv:
    __androidRoot = None
    __javaHome = None
    __hostMakeFilePath = None
    __macSdkVersion = None
    __jniGeneratorPath = None

    def setAndroidRoot(self, androidRoot):
        self.__androidRoot = androidRoot
        self.__hostMakeFilePath = self.__androidRoot + r"/build/core/combo/HOST_darwin-x86.mk"

        # 如果原件存在，则将原件拷贝名为HOST_darwin-x86.mk的文件
        origHostMakeFilePath = self.__hostMakeFilePath + ".orig"
        if (os.path.isfile(origHostMakeFilePath)):
            shutil.copy(origHostMakeFilePath, self.__hostMakeFilePath)

        # 获得当前Android源码支持的mac sdk版本
        macSdkVersionSupported = self.__getMacSdkVersionSupported(buildEnv.getHostMakeFilePath())
        #print("macSdkVersionSupported: %s" % macSdkVersionSupported)
        # get mac sdk version
        status, macSdkVersionsInstalled = commands.getstatusoutput(r'xcodebuild -showsdks | grep macosx | sort | sed -e "s/.*macosx//g"')
        macSdkVersionsInstalled = macSdkVersionsInstalled.splitlines();
        # 查找mac中是否有Android源码所支持的sdk版本
        for sdkVersion in macSdkVersionSupported:
            if sdkVersion in macSdkVersionsInstalled:
                self.__macSdkVersion = sdkVersion
                break;

        # 判断是否找到合适的SDK版本
        if (None == self.__macSdkVersion):
            self.__macSdkVersion = macSdkVersionsInstalled[0]
        #print(self.__macSdkVersion)
        #print("status=%d result=%s" % (status, macSdkVersionsInstalled))

        # 如果原件存在，则将原件拷贝名为jni_generator.py的文件
        self.__jniGeneratorPath = self.__androidRoot + r"/external/chromium_org/base/android/jni_generator/jni_generator.py"
        origJniGeneratorPath = self.__jniGeneratorPath + ".orig"
        if (os.path.isfile(origJniGeneratorPath)):
            shutil.copy(origJniGeneratorPath, self.__jniGeneratorPath)

    def setJavaHome(self, javaHome):
        javaBin = javaHome + os.sep + "bin" + os.sep + "java"
        result = commands.getoutput(javaBin + " -version")
        result = result.split('\n')[0]
        pattern = re.compile(r'java version "1\.6')
        match = pattern.match(result)
        if (None == match):
            raise Exception("java home not java6 home")
        self.__javaHome = javaHome

    def getJavaHome(self):
        return self.__javaHome

    def getHostMakeFilePath(self):
        return self.__hostMakeFilePath

    def getMacSdkVersion(self):
        return self.__macSdkVersion

    def getJniGeneratorPath(self):
        return self.__jniGeneratorPath

    # 获得当前Android源码支持的mac sdk版本
    # 获得成功，则返回Android源码支持的mac sdk版本列表；获得失败，则返回None
    def __getMacSdkVersionSupported(self, filePath):
        result=None
        with open(filePath) as file:
            while 1:
                line = file.readline()
                index = line.find(r"mac_sdk_versions_supported :=")
                if (0 == index):
                    line = line[len(r"mac_sdk_versions_supported :="):].strip()
                    result = line.split(" ")
                    break
                if not line:
                    break
                pass # do something

        return result

class MacAndroidBuildEnvImpl:
    __macBuildEnv=None

    def __init__(self, macBuildEnv):
        self.__macBuildEnv = macBuildEnv

    def process(self):
        # 设置java6的环境变量
        self.setJava6Env()
        # 修改HOST_darwin-x86.mk
        self.__modifyHostMakeFile()
        # 修改jni_generator.py文件
        self.__modifyJniGenerator()

    '''
    设置java6的环境变量
    '''
    def setJava6Env(self):
        javaHome = self.__macBuildEnv.getJavaHome()
        if (None != javaHome):
            # 导出java6的环境变量
            os.environ['JAVA_HOME'] = javaHome;
            os.environ['PATH'] = os.environ['JAVA_HOME'] + os.sep + "bin:" + os.environ['PATH']

    '''
    修改HOST_darwin-x86.mk
    '''
    def __modifyHostMakeFile(self):
        hostMakeFilePath = self.__macBuildEnv.getHostMakeFilePath()
        origHostMakeFilePath = hostMakeFilePath + ".orig"   # 用于保存原件
        newHostMakeFilePath = hostMakeFilePath + ".new"
        macSdkVersion = self.__macBuildEnv.getMacSdkVersion()

        # 如果没有保存原件，则先保存原件
        if (False == os.path.isfile(origHostMakeFilePath)):
            shutil.copy(hostMakeFilePath, origHostMakeFilePath)

        with open(hostMakeFilePath, 'r') as f:
            with open(newHostMakeFilePath, 'w') as g:
                for line in f.readlines():
                    index = line.find(r"mac_sdk_versions_supported :=")
                    if (0 == index):
                        line = r"mac_sdk_versions_supported := " + macSdkVersion + "\n"
                    elif (0 == line.find(r"ifeq ($(mac_sdk_version),10.8)")):
                        line = r"ifeq ($(mac_sdk_version)," + macSdkVersion + r")" + "\n"
                    g.write(line)

        # 将新文件更名为HOST_darwin-x86.mk
        shutil.move(newHostMakeFilePath, hostMakeFilePath)

    '''
    修改jni_generator.py文件
    '''
    def __modifyJniGenerator(self):
        filePath = self.__macBuildEnv.getJniGeneratorPath()
        origFilePath = filePath + ".orig"
        newFilePath = filePath + ".new"

        # 如果没有保存原件，则先保存原件
        if (False == os.path.isfile(origFilePath)):
            shutil.copy(filePath, origFilePath)

        with open(filePath, 'r') as f:
            with open(newFilePath, 'w') as g:
                for line in f.readlines():
                    if (0 == line.find(r"class JNIFromJavaSource(object):")):
                        g.write("import platform\n")
                        g.write(line)
                    else:
                        index = line.find(r"p = subprocess.Popen(args=['cpp', '-fpreprocessed'],")
                        if (-1 != index):
                            spaces = line[0:index]
                            g.write(spaces + r"system = platform.system()" + "\n")
                            g.write(spaces + r"if system == 'Darwin':" + "\n")
                            g.write(spaces + "    " + r"cpp_args = ['cpp']" + "\n")
                            g.write(spaces + "else:\n")
                            g.write(spaces + "    " + r"cpp_args = ['cpp', '-fpreprocessed']" + "\n")
                            g.write(spaces + r"p = subprocess.Popen(args=cpp_args," + "\n")
                        else:
                            g.write(line)

        # 将新文件更名为jni_generator.py
        shutil.move(newFilePath, filePath)

def usage():
    print("Usage:%s" % sys.argv[0])
    print("-h")
    print("[-d <android src root>] [-j <java home>]")

try:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    logging.StreamHandler(sys.stdout)
    logging.info("------ start process ------")

    androidRoot = None
    javaHome = None
    # 命令行解析
    options, remainder = getopt.getopt(sys.argv[1:], 'd:j:')
    for opt, arg in options:
        if opt in ("-h"):
            usage()
            sys.exit(1)
        elif opt in ("-d"):
            androidRoot = arg
        elif opt in ("-j"):
            javaHome = arg
        else:
            usage()
            sys.exit(1)

    if (None == androidRoot):
        androidRoot = os.path.split(os.path.realpath(__file__))[0]

    buildEnv = MacAndroidBuildEnv()
    buildEnv.setAndroidRoot(androidRoot)
    if (None != javaHome):
        buildEnv.setJavaHome(javaHome)

    buildEnvImpl = MacAndroidBuildEnvImpl(buildEnv)
    buildEnvImpl.process()

    logging.info("------ end process ------")
except Exception as err:
    print 'ERROR:', err
    sys.exit(1)