ARG CONTRAIL_REGISTRY
ARG CONTRAIL_CONTAINER_TAG
FROM ${CONTRAIL_REGISTRY}/contrail-base:${CONTRAIL_CONTAINER_TAG}

ARG SITE_MIRROR
ARG YUM_ENABLE_REPOS=""
ARG SKU=ocata
ARG OPENSTACK_REPO
ARG CONTRAIL_REPO
ARG DOCKERFILE_DIR

COPY $DOCKERFILE_DIR/*requirements*.txt $DOCKERFILE_DIR/entrypoint.sh /

RUN mkdir -p /contrail-test
COPY $DOCKERFILE_DIR/prepare_repos.sh /etc/yum.repos.d/
COPY ./ /contrail-test/

# install most packages from pypi and only then python-Fabric
RUN \
    source /etc/os-release && \
    source /functions.sh && \
    if [[ "$ID" == 'rhel' && "$VERSION_ID" == '8.4' ]] ; then \
      yum module enable -y javapackages-tools ; \
    fi && \
    source /functions.sh && \
    yum update -y -x "redhat-release*" -x "coreutils*" && \
    yum -y update-minimal --security --sec-severity=Important --sec-severity=Critical && \
    yum install -y unzip vim tcpdump ant git ipmitool \
      patch bzip2 sudo ant-junit libXpm libXrender \
      gtk2 GConf2 gcc-c++ && \
    SSHPASS_RPM_NAME=sshpass-1.06-9.el8.x86_64.rpm && \
    download_package https://archives.fedoraproject.org pub/archive/epel/8.4/Everything/x86_64/Packages/s/${SSHPASS_RPM_NAME} ${SSHPASS_RPM_NAME} && \
    rpm -Uvh --nodeps --replacepkgs ${SSHPASS_RPM_NAME} && \
    yum install -y python3-devel && \
    /etc/yum.repos.d/prepare_repos.sh && \
    yum install -y python3-contrail && \
    python3 -m pip install -r /requirements_common.txt -r /requirements3.txt && \
    yum clean all -y && \
    rm -rf /var/cache/yum && \
    rm -rf /etc/yum.repos.d && \
    mkdir -p /contrail-test/images

ENTRYPOINT ["/entrypoint.sh"]

LABEL net.juniper.contrail=test
LABEL net.juniper.node=test
