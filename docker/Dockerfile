ARG CONTRAIL_REGISTRY
ARG CONTRAIL_CONTAINER_TAG
FROM ${CONTRAIL_REGISTRY}/opensdn-base:${CONTRAIL_CONTAINER_TAG}
ARG PIP_REPOSITORY

ARG DOCKERFILE_DIR

COPY $DOCKERFILE_DIR/*requirements*.txt $DOCKERFILE_DIR/entrypoint.sh /

RUN mkdir -p /contrail-test
COPY ./ /contrail-test/

# install most packages from pypi and only then python-Fabric
RUN set -e ; \
    source /etc/os-release ; \
    source /functions.sh ; \
    dnf update -y -x "redhat-release*" -x "coreutils*" ; \
    dnf -y update-minimal --security --sec-severity=Important --sec-severity=Critical ; \
    dnf install -y unzip vim tcpdump ant git ipmitool \
      patch bzip2 sudo ant-junit libXpm libXrender \
      gtk2 GConf2 sshpass libffi-devel; \
      # legacy crypto policies are required for ssh to cirros images
      update-crypto-policies --set LEGACY ; \
    dnf clean all -y ; \
    rm -rf /var/cache/yum ; \
    rm -rf /etc/yum.repos.d ; \
    # test's code writes to this file and fails if dir is absent
    mkdir -p /etc/contrail/ ; \
    touch /etc/contrail/vnc_api_lib.ini ; \
    python3 -m pip install --no-compile -r /requirements_common.txt -r /requirements3.txt ; \
    mkdir -p /contrail-test/images

ENTRYPOINT ["/entrypoint.sh"]

LABEL net.juniper.contrail=test
LABEL net.juniper.node=test
